"""File analysis crawler component."""


from illume import config
from illume.actor import Actor
from illume.error import FileNotFound
from illume.parse.link_fsm import DocumentReaderFsm, LEGAL_URL_CHARS
from os.path import exists
from urllib.parse import urlsplit, urlunsplit, quote, quote_plus, urljoin


SCHEME = 0
NETLOC = 1
PATH = 2
QUERY = 3
FRAGMENT = 4


class FileAnalyzer(Actor):

    """File analyzer actor."""

    def on_init(self):
        self.drop_fragments = config.get("PARSER_DROP_FRAGMENTS")
        self.drop_query = config.get("PARSER_DROP_QUERY")

    async def on_message(self, message):
        path = message.get("path", None)
        origin = message.get("domain", None)

        if not exists(path):
            raise FileNotFound(path)

        stream = open(path)
        fsm = DocumentReaderFsm(stream)

        fsm.perform()

        message.update({"urls": self.parse_urls(origin, fsm.matches)})

        await self.publish(message)

    def parse_urls(self, origin_url, urls):
        result = []
        origin_metadata = urlsplit(origin_url)

        for url in urls:
            url, domain = self.parse_url(origin_metadata, url)
            result.append({
                "url": url,
                "domain": domain
            })

        return result

    def parse_url(self, origin_metadata, url):
        metadata = urlsplit(url)
        tokens = list(metadata)
        domains_match = tokens[NETLOC] == origin_metadata.netloc

        # Fill in the domain.
        if not tokens[NETLOC]:
            # TODO determine if url based on the TLD
            if ":" in tokens[PATH]:
                tokens[NETLOC] = tokens[PATH]
            elif "/" in tokens[PATH] and "." in tokens[PATH]:
                url = "http://" + tokens[PATH]
                metadata = urlsplit(url)
                tokens = list(metadata)
            else:
                tokens[PATH] = urljoin(origin_metadata.path, tokens[PATH])
                tokens[NETLOC] = origin_metadata[NETLOC]
                domains_match = True

        if not domains_match:
            tokens[NETLOC] = tokens[NETLOC].encode("idna").decode("utf-8")

        # Fill in the scheme
        if not tokens[SCHEME] and domains_match:
            tokens[SCHEME] = origin_metadata[SCHEME]
        elif not metadata.scheme:
            # Default to HTTP if there is no scheme.
            tokens[SCHEME] = "http"

        # Escaping the url is definitely not perfect. More work needs to be done
        # here to cover all edge cases.
        tokens[PATH] = quote(tokens[PATH], safe=LEGAL_URL_CHARS)

        if self.drop_query:
            tokens[QUERY] = ''
        else:
            # TODO what happens if there's a plus and a space in the query?
            tokens[QUERY] = quote_plus(tokens[QUERY], safe=LEGAL_URL_CHARS)

        if self.drop_fragments:
            tokens[FRAGMENT] = ''
        else:
            tokens[FRAGMENT] = quote(tokens[FRAGMENT], safe=LEGAL_URL_CHARS)

        return urlunsplit(tokens), tokens[NETLOC]
