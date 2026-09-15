import pathlib
import yaml

DEFAULT_AUDIENCE_PATH = pathlib.Path("audience.yaml")


def load_audience(path: pathlib.Path = DEFAULT_AUDIENCE_PATH) -> dict:
    """audience.yaml을 읽는다. 파일이 없으면 즉시 멈춘다 — 설정 없이
    기본값으로 조용히 도는 것은 눈에 안 띄는 실패이기 때문이다."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} 가 없습니다. audience.yaml을 만들어야 실행할 수 있습니다."
        )
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build_criteria(cfg: dict) -> str:
    out = [f"독자는 {cfg['독자']['누구']}입니다.",
           f"이미 아는 것: {cfg['독자']['이미_아는_것']}",
           "", "중요도 기준 (위에 있을수록 우선):"]
    out += [f"- {x}" for x in cfg["중요도_기준"]]
    out += ["", "버릴 것:"]
    out += [f"- {x}" for x in cfg["버릴_것"]]
    return "\n".join(out)


def topic_names(cfg: dict) -> tuple:
    return tuple(t["이름"] for t in cfg["토픽"])


def build_topic_guide(cfg: dict) -> str:
    lines = ["토픽별 작성 지침:"]
    lines += [f"- {t['이름']}: {t['데스크지침']}" for t in cfg["토픽"]]
    return "\n".join(lines)


def topic_emoji_map(cfg: dict) -> dict:
    return {t["이름"]: t.get("이모지", "📰") for t in cfg["토픽"]}
