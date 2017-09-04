"""Persistent key filter."""


from illume.db import SqliteDB
from illume.error import QueryError


SCHEMA = [
    """
    CREATE TABLE filter (
        domain BINARY({key_size}),
        url BINARY({key_size}),
        PRIMARY KEY (domain, url)
    )
    """,
    "CREATE INDEX domain_idx ON filter (domain)",
    "CREATE INDEX url_idx ON filter (url)",
]


CHECKER = """
    SELECT name FROM sqlite_master
    WHERE (type = 'table' and name = 'filter')
    OR    (type = 'index' and name = 'domain_idx')
    OR    (type = 'index' and name = 'url_idx')
"""


DROPPER = [
    "DROP TABLE filter",
    "DROP INDEX domain_idx",
    "DROP INDEX url_idx;",
]


INSERTER = "INSERT INTO filter (domain, url) VALUES (?, ?)"
INSERTER_MULTI = "INSERT INTO filter (domain, url) VALUES "


CHECKER_URL = "SELECT 1 FROM filter WHERE url = ?"
CHECKER_DOMAIN = "SELECT 1 FROM filter WHERE domain = ?"
CHECKER_BOTH = "SELECT 1 FROM filter WHERE domain = ? AND url = ?"
CHECKER_MULTI = "SELECT domain, url FROM filter WHERE "


class PersistentKeyFilter(SqliteDB):

    """
    Persistent uniqueness filter for domains and URLs.

    Args:
        path (str): Path of database.
        key_size (int): Size of columns used to store hashes.
    """

    def __init__(self, path, key_size=8):
        self.path = path
        self.key_size = key_size

    def check_if_tables_exist(self):
        """Assert existence of tables."""
        result = self._db_conn.execute(CHECKER)

        return sum(1 for x in result) == len(SCHEMA)

    def create_db(self):
        """Create database."""
        table = SCHEMA[0].format(key_size=self.key_size)
        queries = (table,) + tuple(SCHEMA[1:])

        with self._db_conn:
            cursor = self._db_conn.cursor()

            for query in queries:
                cursor.execute(query)

    def add(self, domain, url, cursor=None):
        """Add domain and url pairing to database."""
        if not cursor:
            cursor = self.create_cursor()

        # TODO This needs context management.
        cursor.execute(INSERTER, (domain, url))

    def add_bulk(self, pairs):
        """Add a set of (domain, url) pairings to the database."""
        with self.conn:
            cursor = self.conn.cursor()

            for domain, url in pairs:
                try:
                    cursor.execute(INSERTER, (domain, url))
                    self.conn.commit()

                    yield True
                except self.conn.Error:
                    self.conn.rollback()

                    yield False

    def exists(self, domain=None, url=None):
        """Check if a domain and/or url exists."""
        if domain and url:
            template = CHECKER_BOTH
            params = (domain, url)
        elif domain:
            template = CHECKER_DOMAIN
            params = (domain,)
        elif url:
            template = CHECKER_URL
            params = (url,)
        else:
            raise QueryError("Must specify domain or url.")

        with self.conn:
            cursor = self.conn.execute(template, params)

            return bool(cursor.fetchone())

    def exists_bulk(self, pairs):
        """Check if a set of domain/url pairings exist."""
        params = []
        tokens = []

        for domain, url in pairs:
            if not domain or not url:
                raise QueryError("Must specify a domain and url.")

            sub_tokens = []

            if domain:
                sub_tokens.append("domain = ?")
                params.append(domain)

            if url:
                sub_tokens.append("url = ?")
                params.append(url)

            tokens.append("({})".format(" AND ".join(sub_tokens)))

        parameter_token = " OR ".join(tokens)
        sql = "{} {}".format(CHECKER_MULTI, parameter_token)

        with self.conn:
            for result in self.conn.execute(sql, params):
                yield result

    def exists_domain(self, domain, cursor=None):
        """Check if a domain exists."""
        if not cursor:
            cursor = self.create_cursor()

        cursor.execute(CHECKER_DOMAIN, (domain,))

        return bool(cursor.fetchone())

    def exists_url(self, domain, url, cursor=None):
        """Check if a URL exists."""
        if not cursor:
            cursor = self.create_cursor()

        cursor.execute(CHECKER_BOTH, (domain, url))

        return bool(cursor.fetchone())
