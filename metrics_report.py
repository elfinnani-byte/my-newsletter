import json, pathlib
from collections import Counter
from graph import SOURCES

path = pathlib.Path("store/metrics.jsonl")
rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] \
       if path.exists() else []

if not rows:
    print("아직 기록이 없습니다. run.py를 한 번 이상 돌린 뒤 다시 실행하세요.")
else:
    print(f"쌓인 실행 기록: {len(rows)}줄\n")
    pub = Counter()
    for r in rows:
        pub.update(r["by_source"])
    print(f"{'소스':<12}{'발행 기여':>9}")
    print("-" * 23)
    names = dict.fromkeys(name for name, _ in SOURCES)   # 같은 이름(예: 베리타스알파의 5개 피드)은 한 번만
    for name in names:
        print(f"{name:<12}{pub.get(name, 0):>9}")

    print("\n수집 → 선별 → 취재 → 발행")
    for r in rows[-5:]:
        print(f"  {r['collected']:>4} → {r['picked']:>3} → {r['drafted']:>3}"
              f" → {r['published']:>3}")