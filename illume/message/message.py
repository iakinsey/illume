"""Message Interface.

Batch workload queue interface.
"""


class Messenger:

    """
    Messenger abstract class.

    See `illume.message.queue` for an example implementation.

    TODO Validate that methods are generators?
    """

    def put(self, item, priority):
        raise NotImplementedError

    def get(self, count=1):
        """Get a maximum of `count` items."""
        raise NotImplementedError

    def put_bulk(self, items_with_priority):
        for item, priority in items_with_priority:
            self.put(item, priority)
