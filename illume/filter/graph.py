from illume.db import SqliteDB
from illume.error import QueryError
from itertools import chain
from time import time


SCHEMA = """
    CREATE TABLE graph (
        source TEXT,
        target TEXT,
        observed INTEGER
    )
"""


CHECKER = """
    SELECT name FROM sqlite_master
    WHERE (type = 'table' and name = 'graph')
"""


ADD_TEMPLATE = "INSERT INTO graph (source, target, observed) VALUES {}"
ENTITY_PART = "(?, ?, ?)"


class EntityGraph(SqliteDB):
    def __init__(self, path):
        self.path = path

    def check_if_tables_exist(self):
        """Assert existence of tables."""
        result = self._db_conn.execute(CHECKER)

        return sum(1 for x in result) == 1

    def create_db(self):
        with self._db_conn:
            cursor = self._db_conn.cursor()

            cursor.execute(SCHEMA)

    def add_entities(self, source, targets):
        now = int(time())
        targets = set(targets)
        params = list(chain(*((source, t, now) for t in targets)))
        entities_part = ",".join([ENTITY_PART for n in range(len(targets))])
        query = ADD_TEMPLATE.format(entities_part)
        cursor = self.create_cursor()

        cursor.execute(query, params)
