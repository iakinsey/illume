"""Assertion functions for tests."""


def check_queue(queue, item):
    """Test that the item in the queue matches the given item."""
    data = queue.get(timeout=1)

    assert data == item
