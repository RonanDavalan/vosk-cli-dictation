# Files bornées, politique « jeter le plus ancien ».

import queue

from src.audio_capture import put_drop_oldest


def test_below_capacity_no_drop():
    q = queue.Queue(maxsize=3)
    assert put_drop_oldest(q, "a") is False
    assert put_drop_oldest(q, "b") is False
    assert list(q.queue) == ["a", "b"]


def test_full_queue_drops_oldest_and_reports():
    q = queue.Queue(maxsize=2)
    put_drop_oldest(q, "a")
    put_drop_oldest(q, "b")
    dropped = put_drop_oldest(q, "c")
    assert dropped is True
    # "a" est parti, "b" et "c" restent, la profondeur ne dépasse pas maxsize.
    assert list(q.queue) == ["b", "c"]
    assert q.qsize() == 2


def test_producer_never_blocks_even_under_sustained_overflow():
    q = queue.Queue(maxsize=4)
    drops = 0
    for i in range(1000):
        if put_drop_oldest(q, i):
            drops += 1
    assert q.qsize() == 4
    assert drops == 1000 - 4
    # la file contient les 4 éléments les plus récents
    assert list(q.queue) == [996, 997, 998, 999]
