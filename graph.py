from typing import Literal
import json, pathlib
import json
import trafilatura
from langgraph.types import Send
import operator
import os
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel, Field
from openai import OpenAI
import feedparser, requests, re
from datetime import datetime, timedelta, timezone
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END


class Brief(TypedDict):
    hours: int                              # 수집 시간 창(시간)
    collected: list                         # ① 수집한 기사
    dead: list                              # ① 응답 없었던 소스
    picked: list                            # ② 선별해 남긴 다섯 건
    drafted: Annotated[list, operator.add]  # ③ 취재한 초안 — 워커들이 나눠 채운다
    verified: list                          # ④ 검수를 통과한 것
    log: Annotated[list, operator.add]      # 무슨 일이 있었는지


UA = {"User-Agent": "Mozilla/5.0 (newsletter-agent-course)"}
SOURCES = [
    ("베리타스알파",  "https://www.veritas-a.com/rss/allArticle.xml"),
    ("에듀동아",      "https://edu.donga.com/rss/allArticle.xml"),
    ("한국대학신문",  "https://news.unn.net/rss/allArticle.xml"),
    ("KEDI",          "https://www.kedi.re.kr/khome/main/announce/rssAnnounceData.do?board_sq_no=3"),
]


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def published_at(entry):
    t = entry.get("published_parsed")
    return datetime(*t[:6], tzinfo=timezone.utc) if t else None


def collect(s: dict) -> dict:   # ① 자료 수집 — 빈 노드를 갈아 끼운다
    cutoff = datetime.now(timezone.utc) - timedelta(hours=s["hours"])
    items, dead, seen = [], [], set()
    for name, url in SOURCES:
        try:
            feed = feedparser.parse(requests.get(url, headers=UA, timeout=20).content)
        except Exception:
            dead.append(name)                   # 한 곳이 죽어도 나머지는 계속
            continue
        for e in feed.entries:
            at = published_at(e)
            if not at or at < cutoff:           # 시간 창 밖이거나 날짜가 없으면 버린다
                continue
            key = e.link.split("?")[0].rstrip("/")       # 추적용 꼬리표를 떼고 비교
            if key in seen:
                continue
            seen.add(key)
            items.append({"title": e.title, "url": e.link, "source": name, "at": at,
                          "summary": strip_tags(e.get("summary", ""))[:300]})
    return {"collected": items, "dead": dead,
            "log": [f"① 수집   {s['hours']}시간 창 · {len(items)}건"
                    + (f" · 응답 없음 {dead}" if dead else "")]}

client = OpenAI()

from config import load_audience, build_criteria, topic_names, build_topic_guide, topic_emoji_map

CFG = load_audience()
TOPIC_NAMES = topic_names(CFG)
TOPIC_GUIDE = build_topic_guide(CFG)
TOPIC_EMOJI = topic_emoji_map(CFG)

class Pick(BaseModel):
    index: int = Field(description="후보 목록에서의 번호")
    reason: str = Field(description="왜 골랐는지 한 문장")
    event: str = Field(description="이 기사가 다루는 사건을 짧은 라벨로. 같은 사건이면 같은 라벨")

class Shortlist(BaseModel):
    picks: list[Pick]

BATCH, TARGET = 40, 5          # 예선 묶음 크기, 최종 발행 건수

CRITERIA = build_criteria(CFG)

def ask_picks(items, n):
    listing = "\n".join(f"{i}. [{it['source']}] {it['title']}" for i, it in enumerate(items))
    sys = (f"{CRITERIA}\n\n아래 목록에서 중요한 순서대로 {n}건을 고르세요.\n"
           "같은 사건을 다룬 기사에는 같은 event 라벨을 붙이세요.")
    out = client.chat.completions.parse(
        model="gpt-4.1-mini", temperature=0,
        messages=[{"role": "system", "content": sys},
                  {"role": "user", "content": listing}],
        response_format=Shortlist).choices[0].message.parsed
    return [p for p in out.picks if 0 <= p.index < len(items)]      # 없는 번호는 버린다


def select(s: dict) -> dict:                   # ② 중요도 선별 — 빈 노드를 갈아 끼운다
    items = s["collected"]
    survivors = []
    for i in range(0, len(items), BATCH):       # 예선 — 묶음마다 여덟 건
        chunk = items[i:i + BATCH]
        survivors += [chunk[p.index] for p in ask_picks(chunk, 8)]
    finals = ask_picks(survivors, TARGET)       # 본선 — 한 화면에 놓고 다섯 건

    picked, seen_events, dupes = [], set(), 0
    for p in finals:
        if p.event in seen_events:
            dupes += 1
            continue
        seen_events.add(p.event)
        picked.append({**survivors[p.index], "event": p.event})

    return {"picked": picked,
            "log": [f"② 선별   {len(items)} → 예선 {len(survivors)} → {len(finals)}건"
                    + (f" · 중복사건 제외 {dupes}건" if dupes else "")]}

class Draft(BaseModel):        # 섹션에서 정한 세 칸 + 주제 분류
    headline: str = Field(description="20자 내외의 한국어 헤드라인")
    summary:  str = Field(description="세 문장 요약. ~합니다체, 과장 없이 건조하게")
    why:      str = Field(description="상담 또는 입학사정 업무에 바로 참고할 수 있는 시사점 한 문장")
    topic: Literal[TOPIC_NAMES] = \
        Field(description="여섯 카테고리 중 가장 가까운 것 하나")

REPORT_SYS = (f"당신은 {CFG['독자']['누구']}를 위한 뉴스레터 기자입니다.\n"
              "아래 기사 본문을 읽고 헤드라인·요약·왜 중요한지·주제 분류를 쓰세요.\n"
              "'주목된다·기대를 모은다' 같은 기자체 표현은 쓰지 마세요.\n\n"
              f"{TOPIC_GUIDE}")

def extract_body(url):
    d = trafilatura.fetch_url(url)
    return trafilatura.extract(d) if d else None

def has_korean(text):
    return bool(re.search(r'[가-힣]', text))

def draft(body):
    d = client.chat.completions.parse(
        model="gpt-4.1-mini", temperature=0,
        messages=[{"role": "system", "content": REPORT_SYS},
                  {"role": "user", "content": body[:6000]}],
        response_format=Draft).choices[0].message.parsed
    retried = False
    if not (has_korean(d.headline) and has_korean(d.summary)):
        retried = True
        d = client.chat.completions.parse(
            model="gpt-4.1-mini", temperature=0,
            messages=[{"role": "system", "content": REPORT_SYS},
                      {"role": "user", "content": body[:6000]},
                      {"role": "assistant", "content": d.model_dump_json()},
                      {"role": "user", "content": "headline과 summary가 한국어가 아닙니다. 반드시 한국어로 다시 쓰세요."}],
            response_format=Draft).choices[0].message.parsed
    return d, retried

def fan_report(s: dict):                      # 기사 수만큼 워커를 펼친다
    return [Send("report", {"item": it}) for it in s["picked"]]

def report(s: dict) -> dict:                   # ③ 요약 — 기사 한 건을 맡는다
    it = s["item"]
    body = extract_body(it["url"])
    if not body or len(body) < 600:            # 4강에서 정한 G1 기준선
        return {"drafted": [],
                "log": [f"   취재 제외 {it['source']} · 본문 {len(body or '')}자"]}
    d, retried = draft(body)
    return {"drafted": [{**it, "body": body[:6000], **d.model_dump()}],
            "log": [f"   취재 완료 {it['source']} · {d.headline[:20]}"
                    + (" · 한국어 재요청" if retried else "")]}

class Verdict(BaseModel):
    ok:       bool      = Field(description="요약이 원문에 근거하면 true")
    problems: list[str] = Field(description="근거 없는 부분. 없으면 빈 목록")

SYS_CHECK = ("요약이 원문에서 뒷받침되는지 판정하세요.\n"
             "헤드라인과 요약만 보고 판단하고, 번역이나 단위 환산은 문제가 아닙니다.")

def check(d):
    user = (f"[원문]\n{d['body'][:5000]}\n\n"
            f"[헤드라인]\n{d['headline']}\n\n[요약]\n{d['summary']}")
    return client.chat.completions.parse(
        model="gpt-4.1-mini", temperature=0,
        messages=[{"role": "system", "content": SYS_CHECK},
                  {"role": "user", "content": user}],
        response_format=Verdict).choices[0].message.parsed

def verify(s: dict) -> dict:                  # ④ 검수 — 빈 노드를 갈아 끼운다
    kept, dropped = [], []
    for d in s["drafted"]:
        (kept if check(d).ok else dropped).append(d)
    return {"verified": kept,                 # 리듀서 없는 새 칸에 담는다
            "log": [f"④ 검수   {len(s['drafted'])} → {len(kept)}건"
                    + (f" · 불합격 {[x['source'] for x in dropped]}" if dropped else "")]}

def build_gchat_text(run_id, lead, articles):
    if not articles:                                   # 조용한 날에도 한 줄은 보낸다
        return f"*🗞️ {run_id}*\n오늘은 조용합니다."
    parts = [f"*🗞️ {run_id} · 대입·교육정책 브리핑*"]
    if lead:
        parts.append(lead)
    for i, a in enumerate(articles, 1):
        emoji = TOPIC_EMOJI.get(a.get("topic", ""), "📰")
        block = [f"*{i}. {emoji} {a['headline']}*", a["summary"]]
        if a.get("why"):
            block.append(f"💡 {a['why']}")
        block.append(f"<{a['url']}|원문 보기> · {a.get('topic', '')} · {a['source']} · {a['when']}")
        parts.append("\n".join(block))
    return "\n\n".join(parts)

def send(run_id, lead, articles, webhook=None, dry_run=True):
    text = build_gchat_text(run_id, lead, articles)
    if dry_run or not webhook:
        print(f"[dry-run] 메시지 {len(text)}자 — 보내지 않음")
        print(text[:400])
        return False
    r = requests.post(webhook, json={"text": text}, timeout=20)
    ok = r.status_code == 200
    print("발행:", "성공" if ok else f"실패 {r.status_code} {r.text[:120]}")
    return ok

def make_lead(arts, dead=None):
    if arts:
        srcs = ", ".join(dict.fromkeys(a["source"] for a in arts))
        lead = f"오늘은 {len(arts)}건을 골랐습니다. ({srcs})"
    else:
        lead = ""
    if dead:
        lead += f"\n⚠️ 응답 없음: {', '.join(dead)}"
    return lead

def publish(s: dict) -> dict:                 # ⑤ 발행 — 마지막 빈 노드
    arts = [{"headline": a["headline"], "summary": a["summary"], "why": a["why"],
             "url": a["url"], "source": a["source"], "topic": a.get("topic", ""),
             "when": a["at"].strftime("%m-%d %H:%M")} for a in s["verified"]]
    today = datetime.now().strftime("%Y-%m-%d")
    sent  = send(today, make_lead(arts, s.get("dead")), arts,
                 webhook=os.environ.get("GCHAT_WEBHOOK_URL"),
                 dry_run=os.environ.get("DRY_RUN", "1") == "1")   # 기본은 보내지 않음
    label = f"{len(arts)}건" if arts else "조용합니다"
    return {"log": [f"⑤ 발행   {label} · {'보냄' if sent else 'dry-run'}"]}

def build():
    g = StateGraph(Brief)
    for name in ("collect", "select", "report", "verify", "publish"):
        g.add_node(name, globals()[name])
    g.add_edge(START, "collect")
    g.add_edge("collect", "select")
    g.add_conditional_edges("select", fan_report, ["report"])   # 고정 엣지가 아니라 팬아웃
    g.add_edge("report", "verify")
    g.add_edge("verify", "publish")
    g.add_edge("publish", END)
    return g

INIT = {"hours": 24,
         "collected": [], "dead": [], "picked": [], "drafted": [], "verified": [], "log": []}


def run():                                     # 돌리고, 한 줄 남긴다
    out = build().compile().invoke(INIT)
    row = {"run_id":    datetime.now().strftime("%Y-%m-%d %H:%M"),
           "collected": len(out["collected"]),
           "picked":    len(out["picked"]),
           "drafted":   len(out["drafted"]),
           "published": len(out["verified"]),
           "hours":     out["hours"],
           "by_source": {},
           "log":       out["log"]}
    for a in out["verified"]:
        row["by_source"][a["source"]] = row["by_source"].get(a["source"], 0) + 1
    path = pathlib.Path("store/metrics.jsonl")
    path.parent.mkdir(exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return out