from graph import append_metrics_row


def test_append_metrics_row_writes_utf8_and_is_readable_back(tmp_path):
    p = tmp_path / "metrics.jsonl"
    append_metrics_row({"run_id": "2026-09-15 09:00", "by_source": {"베리타스알파": 1}}, p)
    # 명시적으로 utf-8로 읽어서 깨지지 않아야 한다 — 인코딩을 안 지정하면
    # 운영체제 기본 인코딩(예: 윈도우 cp949)으로 써져서 다른 환경(예: Linux CI)에서
    # 읽을 때 깨지는 문제가 있었다.
    content = p.read_text(encoding="utf-8")
    assert "베리타스알파" in content


def test_append_metrics_row_appends_multiple_lines(tmp_path):
    p = tmp_path / "metrics.jsonl"
    append_metrics_row({"run_id": "1"}, p)
    append_metrics_row({"run_id": "2"}, p)
    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_append_metrics_row_creates_parent_directory(tmp_path):
    p = tmp_path / "nested" / "metrics.jsonl"
    append_metrics_row({"run_id": "1"}, p)
    assert p.exists()
