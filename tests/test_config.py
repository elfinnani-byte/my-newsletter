import pathlib
import pytest
from config import load_audience, build_criteria, topic_names, build_topic_guide, topic_emoji_map


def test_load_audience_missing_file_raises(tmp_path):
    missing = tmp_path / "no_such_audience.yaml"
    with pytest.raises(FileNotFoundError):
        load_audience(missing)


def test_load_audience_reads_yaml(tmp_path):
    p = tmp_path / "audience.yaml"
    p.write_text(
        "독자:\n  누구: \"테스트 독자\"\n  이미_아는_것: \"테스트 지식\"\n"
        "중요도_기준:\n  - \"기준1\"\n"
        "버릴_것:\n  - \"버릴것1\"\n"
        "토픽:\n  - 이름: \"토픽A\"\n    데스크지침: \"지침A\"\n",
        encoding="utf-8",
    )
    cfg = load_audience(p)
    assert cfg["독자"]["누구"] == "테스트 독자"


def test_build_criteria_includes_reader_and_rules():
    cfg = {
        "독자": {"누구": "테스트 독자", "이미_아는_것": "테스트 지식"},
        "중요도_기준": ["기준1", "기준2"],
        "버릴_것": ["버릴것1"],
    }
    text = build_criteria(cfg)
    assert "테스트 독자" in text
    assert "기준1" in text and "기준2" in text
    assert "버릴것1" in text


def test_topic_names_returns_tuple_in_order():
    cfg = {"토픽": [{"이름": "A", "데스크지침": "a"}, {"이름": "B", "데스크지침": "b"}]}
    assert topic_names(cfg) == ("A", "B")


def test_build_topic_guide_lists_every_topic_with_guidance():
    cfg = {"토픽": [{"이름": "A", "데스크지침": "가이드A"}]}
    guide = build_topic_guide(cfg)
    assert "A" in guide
    assert "가이드A" in guide


def test_topic_emoji_map_returns_emoji_per_topic():
    cfg = {"토픽": [{"이름": "A", "데스크지침": "a", "이모지": "📋"},
                    {"이름": "B", "데스크지침": "b", "이모지": "🎓"}]}
    emap = topic_emoji_map(cfg)
    assert emap == {"A": "📋", "B": "🎓"}


def test_topic_emoji_map_defaults_when_missing():
    cfg = {"토픽": [{"이름": "A", "데스크지침": "a"}]}
    emap = topic_emoji_map(cfg)
    assert emap["A"] == "📰"
