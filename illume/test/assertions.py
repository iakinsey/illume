"""Assertion functions for tests."""


from queue import Empty


def check_queue(queue, item):
    """Test that the item in the queue matches the given item."""
    data = queue.get(timeout=1)

    assert data == item


def check_queue_multi(queue, items, check_empty=True):
    """Test that all items in the queue match the set of items."""
    for item in items:
        check_queue(queue, item)

    if check_empty:
        assert queue.empty()

def dict_equals(expected, actual):
    """Test that 2 dicts are equal."""

    return len(set(expected.items()) ^ set(actual.items())) == 0
