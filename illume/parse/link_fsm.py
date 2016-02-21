"""Implements a finite state machine that extracts URLs from a stream."""


class FSMExit(Exception):
    """Raise this exception to gracefully exit from the FSM."""
    pass


class FSM:
    _state = None

    def __init__(self, stream, matches=None):
        self.stream = stream
        self.running = False
        self.state = self.initial_state

        if matches is None:
            self.matches = set()
        else:
            self.matches = matches

        self.on_init()

    def on_init(self):
        """Instantiation event hook."""
        pass

    def reset(self):
        self.state = self.initial_state

    @property
    def initial_state(self):
        raise NotImplementedError("Initial state must be set for FSM to run.")

    def get_bytes(self, size, term_char=None):
        data = self.stream.read(size)
        terminates = False

        if term_char is not None:
            terminates = term_char in data

        end = len(data) == size

        return data, terminates, end

    def read_until_match(self, string, term_chars='', rewind=True):
        """
        Read from the buffer until the specified string is matched.

        Returns `True` if string is found.
        Returns `False` if string is not found or term_chars are matched.

        If rewind is set to `True`, set the buffer's cursor to its initial
        value when this function was first called.
        """
        index = 0
        char = string[index]
        str_size = len(string)
        position = self.stream.tell()

        while 1:
            data = self.stream.read(1)

            if data == char:
                index += 1

                if index == str_size:
                    return True

                char = string[index]
            elif data in term_chars or data == "":
                if rewind:
                    self.stream.seek(position)

                return False

    def read_until_match_chars(self, chars, term_chars='', rewind=True):
        """
        Read from the buffer until a char in chars or term_chars if found.

        Returns char if character matches a character in argument `chars`.
        Returns `None` if character matches a character in `term_chars`.
        Returns `None` if character is not found.

        If rewind is set to `True`, set the buffer's cursor to its initial
        value when this function was first called.
        """

        position = self.stream.tell()

        while 1:
            data = self.stream.read(1)
            if data == "":
                if rewind:
                    self.stream.seek(position)
                    return

            for char in chars:
                if data == char:
                    return char

            for char in term_chars:
                if data == char:
                    if rewind:
                        self.stream.seek(position)

                    return

    def match_next_or(self, chars, rewind=True):
        """
        Assert that the next character in the buffer is in the set of argument
        `chars`.

        Returns character if character is in `chars`.
        Returns None if no match.
        """

        position = self.stream.tell()

        data = self.stream.read(1)

        for char in chars:
            if data == char:
                return data

        if rewind:
            self.stream.seek(position)

    def match_next(self, string, rewind=True):
        """
        Assert that the next characters in the buffer match argument `string`.

        Returns `True` if match is found.
        Returns `False` if no match is found.
        """

        position = self.stream.tell()

        for char in string:
            data = self.stream.read(1)

            if char != data:
                if rewind:
                    self.stream.seek(position)

                return

        return string

    def get_until(self, term_chars):
        """
        Read from the buffer and return all characters between the start of the
        cursor and the end of the document or first instance of a character
        specified in `term_chars`.
        """
        result = []

        while 1:
            data = self.stream.read(1)

            if data in term_chars or data == "":
                return "".join(result)

            result.append(data)

    def get_until_mismatch(self, legal_chars):
        """
        Read from the buffer and return all characters between the start of the
        cursor and the end of the document for the first instance of a character
        not specified in `term_chars`.
        """
        result = []

        while 1:
            data = self.stream.read(1)

            if data not in legal_chars or data == "":
                return "".join(result)

            result.append(data)

    def perform(self):
        self.running = True

        try:
            while self.state != self.end:
                self.state()
        except FSMExit:
            pass

        self.running = False

        self.end()
        self.reset()

    def exit(self):
        self.state = self.end

        raise FSMExit()

    def end(self):
        pass


class LinkReaderFsm(FSM):
    http = "http"
    ttp = "ttp"
    https_suffix = 's'
    final_http_suffix = ':'
    double_forward_slash = "//"
    follows_http = https_suffix + final_http_suffix
    legal_url_chars = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789"
        "-._~:/?#[]@!$%&'()*+,;="
    )

    @property
    def initial_state(self):
        return self.read_link

    def read_link(self):
        data = []

        if not self.match_next(self.ttp):
            self.exit()

        next_char = self.match_next_or(self.follows_http)

        if next_char is None:
            return

        data.append(self.http)

        if next_char == self.https_suffix:
            data.append(self.https_suffix)

            next_char = self.match_next(self.final_http_suffix)

        if next_char != self.final_http_suffix:
            return

        data.append(self.final_http_suffix)

        if not self.match_next(self.double_forward_slash):
            return

        data.append(self.double_forward_slash)

        # This obeys RFC 3986 when matching a URL. However, pages may not follow
        # the specification. It would be a good idea to find a more inclusive
        # pattern for extracting URLS in the future
        url = self.get_until_mismatch(self.legal_url_chars)

        if url:
            data.append(url)
            self.matches.add("".join(data))


class TagReaderFsm(FSM):
    a = "a"
    href = "href="
    a_terminates = ">\"'"
    close_tag = ">"
    tag_quotes = "'\""

    @property
    def initial_state(self):
        return self.read_tag

    def read_tag(self):
        if self.match_next(self.a):
            self.state = self.read_a_tag
        else:
            self.exit()

    def read_a_tag(self):
        if not self.read_until_match(self.href, self.close_tag):
            self.exit()

        if not self.match_next_or(self.tag_quotes):
            self.exit()

        url = self.get_until(self.a_terminates)

        if url:
            self.matches.add(url)


class DocumentReaderFsm(FSM):
    http_prefix = "h"
    tag_prefix = "<"
    url_hint = http_prefix + tag_prefix

    def on_init(self):
        self.tag_reader = TagReaderFsm(self.stream, matches=self.matches)
        self.link_reader = LinkReaderFsm(self.stream, matches=self.matches)

    @property
    def initial_state(self):
        return self.read_document

    def read_document(self):
        next_char = self.read_until_match_chars(self.url_hint)

        if not next_char:
            self.exit()
        elif next_char == self.tag_prefix:
            self.tag_reader.perform()
        elif next_char == self.http_prefix:
            self.link_reader.perform()
