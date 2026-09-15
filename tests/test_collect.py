from datetime import timezone, timedelta
from graph import published_at

KST = timezone(timedelta(hours=9))


def test_published_at_full_datetime_uses_utc():
    entry = {
        "published": "Mon, 15 Sep 2026 10:00:00 +0000",
        "published_parsed": (2026, 9, 15, 10, 0, 0, 0, 0, 0),
    }
    at = published_at(entry)
    assert at.tzinfo == timezone.utc
    assert at.hour == 10


def test_published_at_date_only_treated_as_end_of_kst_day():
    entry = {
        "published": "2026-09-14",
        "published_parsed": (2026, 9, 14, 0, 0, 0, 0, 0, 0),
    }
    at = published_at(entry)
    assert at.tzinfo == KST
    # 하루 중 언제 올라왔을지 모르므로, 그날이 끝나는 시각(23:59:59)으로 가정해
    # 컷오프 경계에서 부당하게 제외되지 않게 한다.
    assert (at.hour, at.minute, at.second) == (23, 59, 59)


def test_published_at_missing_returns_none():
    assert published_at({}) is None
