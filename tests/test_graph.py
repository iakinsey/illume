from illume import config
from illume.filter.graph import EntityGraph
from os.path import join
from uuid import uuid1


class TestGraph:
    def test_create_tables(self):
        db = self.create_db()
        db._init_db()

        assert db.check_if_tables_exist()

    def test_add_entities(self):
        db = self.create_db()
        source = "source"
        targets = sorted([str(uuid1()) for n in range(100)])
        db.add_entities(source, targets)

        query = "SELECT source, target, observed FROM graph"
        cursor = db.conn.cursor()

        cursor.execute(query)
        result = list(cursor.fetchall())
        uuids = sorted([i[1] for i in result])

        assert len(result) == len(targets)
        assert all(i[2] == result[0][2] for i in result)
        assert set(uuids) == set(targets)

    def create_db(self):
        # Create/check test folder.
        path = join(config.get("DATA_DIR"), "entity_graph-{}".format(uuid1()))

        # Create database file.
        return EntityGraph(path)
