from illume.error import DatabaseCorrupt, QueryError
from illume.util import create_dir
from os.path import dirname, exists
from sqlite3 import connect


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


class PersistentKeyFilter(object):
    _db_conn = None

    def __init__(self, path, key_size=8):
        self.path = path
        self.key_size = key_size

    @property
    def conn(self):
        if self._db_conn is None:
            self._init_db()

        return self._db_conn

    def _init_db(self):
        db_exists = exists(self.path)
        create_dir(dirname(self.path))
        self._db_conn = connect(self.path)

        if not db_exists:
            # Database needs to be set up.
            self._create_db()
        elif not self.check_if_tables_exist():
            # Database is corrupt.
            raise DatabaseCorrupt("Tables out of sync.")

    def _check_if_tables_exist(self):
        result = self._db_conn.execute(CHECKER)

        return sum(1 for x in result) == len(SCHEMA)

    def _create_db(self):
        table = SCHEMA[0].format(key_size=self.key_size)
        queries = (table,) + tuple(SCHEMA[1:])

        with self._db_conn:
            cursor = self._db_conn.cursor()

            for query in queries:
                cursor.execute(query)

    def create_cursor(self):
        return self.conn.cursor()

    def add(self, domain, url):
        with self.conn:
            self.conn.execute(INSERTER, (domain, url))

    def add_bulk(self, pairs):
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
        if not cursor:
            cursor = self.create_cursor()

        cursor.execute(CHECKER_DOMAIN, (domain,))

        return bool(cursor.fetchone())

    def exists_url(self, domain, url, cursor=None):
        if not cursor:
            cursor = self.create_cursor()

        cursor.execute(CHECKER_BOTH, (domain, url))

        return bool(cursor.fetchone())
