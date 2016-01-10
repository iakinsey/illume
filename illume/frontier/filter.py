from illume.actor import Actor
from illume.error import DatabaseCorrupt


class KeyFilter(Actor):
    def on_init(self):
        self.init_bloom_filter()
        self.init_db()

    def init_bloom_filter(self):
        pass

    def init_db(self):
        pass

    def on_message(self, message):
        # Get a set of messages.
        # Check to see if they exist in the bloom filter.
        # Add them if they dont show up.

        # If it didn't exist it in the bloom filter, add it to the database and
        # bloom filter then push it to the outbox.

        # If it did exist in the bloom filter, double check with the database

        # If it exists in the database, continue.

        # If it didn't exist, add it to the database and then push it to the
        # outbox.

        # If the bloom filter exceeds it's maximum size or error rate, a new
        # one is created and the bloom filter is reindexed. A warning is
        # triggered with the new values.

        pass
