"""Sqlite3 database interface."""


from illume.error import DatabaseCorrupt
from illume.util import create_dir
from os.path import dirname, exists
from sqlite3 import connect


class SqliteDB(object):

    """Interface for Sqlite3 databases."""

    path = None
    _db_conn = None

    @property
    def conn(self):
        """Database connection."""
        if self._db_conn is None:
            self._init_db()

        return self._db_conn

    def _init_db(self):
        """Initialize database, create if it doesn't exist."""
        db_exists = exists(self.path)
        create_dir(dirname(self.path))
        self._db_conn = connect(self.path)

        if not db_exists:
            # Database needs to be set up.
            self.create_db()
        elif not self.check_if_tables_exist():
            # Database is corrupt.
            raise DatabaseCorrupt("Tables out of sync.")

    def check_if_tables_exist(self):
        """Assert existence of tables."""
        return True

    def create_db(self):
        """Create database."""
        raise NotImplementedError()

    def create_cursor(self):
        """Database cursor."""
        return self.conn.cursor()
