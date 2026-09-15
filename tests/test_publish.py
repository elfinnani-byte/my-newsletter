from graph import build_gchat_text


def test_build_gchat_text_no_articles_says_quiet():
    text = build_gchat_text("2026-09-15", "", [])
    assert "조용합니다" in text


def test_build_gchat_text_includes_headline_and_link():
    articles = [{
        "headline": "테스트 헤드라인",
        "summary": "테스트 요약입니다.",
        "why": "테스트 이유입니다.",
        "url": "https://example.com/a",
        "source": "테스트소스",
        "topic": "입시제도·정책",
        "when": "09-15 09:00",
    }]
    text = build_gchat_text("2026-09-15", "오늘은 1건입니다.", articles)
    assert "테스트 헤드라인" in text
    assert "https://example.com/a" in text
    assert "테스트소스" in text
    assert "오늘은 1건입니다." in text


def test_build_gchat_text_numbers_multiple_articles():
    articles = [
        {"headline": "첫번째", "summary": "s1", "why": "w1",
         "url": "https://example.com/1", "source": "A", "topic": "대학 소식", "when": "09-15 09:00"},
        {"headline": "두번째", "summary": "s2", "why": "w2",
         "url": "https://example.com/2", "source": "B", "topic": "대학 소식", "when": "09-15 09:10"},
    ]
    text = build_gchat_text("2026-09-15", "", articles)
    assert "*1. 첫번째*" in text
    assert "*2. 두번째*" in text
