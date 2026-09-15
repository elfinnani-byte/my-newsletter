from graph import backfill_minimum


def test_backfill_minimum_fills_up_to_target_from_survivors():
    picked = [{"url": "https://a", "source": "A", "title": "픽된 기사"}]
    survivors = [
        {"url": "https://a", "source": "A", "title": "픽된 기사"},
        {"url": "https://b", "source": "B", "title": "보충 후보 1"},
        {"url": "https://c", "source": "C", "title": "보충 후보 2"},
        {"url": "https://d", "source": "D", "title": "보충 후보 3"},
    ]
    filled = backfill_minimum(picked, survivors, 3)
    assert len(filled) == 3
    urls = [p["url"] for p in filled]
    assert urls == ["https://a", "https://b", "https://c"]


def test_backfill_minimum_does_not_duplicate_already_picked():
    picked = [{"url": "https://a", "source": "A", "title": "픽된 기사"}]
    survivors = [{"url": "https://a", "source": "A", "title": "픽된 기사"}]
    filled = backfill_minimum(picked, survivors, 3)
    assert len(filled) == 1


def test_backfill_minimum_noop_when_already_at_target():
    picked = [
        {"url": "https://a", "source": "A", "title": "1"},
        {"url": "https://b", "source": "B", "title": "2"},
        {"url": "https://c", "source": "C", "title": "3"},
    ]
    survivors = picked + [{"url": "https://d", "source": "D", "title": "4"}]
    filled = backfill_minimum(picked, survivors, 3)
    assert len(filled) == 3


def test_backfill_minimum_stops_at_available_survivors():
    picked = [{"url": "https://a", "source": "A", "title": "픽된 기사"}]
    survivors = [{"url": "https://a", "source": "A", "title": "픽된 기사"}]
    filled = backfill_minimum(picked, survivors, 5)
    assert len(filled) == 1
