"""dist/ 에셋과 layout.json으로 아바타 PNG를 합성 (Gradio 데모·미리보기용)."""

import json
from functools import lru_cache
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent
DIST = ROOT / "dist"

FACES = {"강아지상": "puppy", "고양이상": "cat", "햄스터상": "hamster", "사슴상": "deer", "토끼상": "rabbit", "여우상": "fox"}
HAIR = {
    "긴 생머리": "long-straight", "긴 웨이브": "long-wave", "허쉬컷": "hush-cut",
    "단발": "bob", "포니테일": "ponytail", "숏 레이어드": "short-layered", "번 헤어": None,
}
BODIES = {
    "굴곡형": "hourglass", "하체 중심형": "pear", "상체 중심형": "inverted-triangle",
    "일자형": "rectangle", "둥근 체형": "oval", "탄탄한 체형": "athletic",
}

# 골격 좌표(발바닥 y=900, 몸 중심 x=0)에서 잘라낼 영역
VIEW = (-230.0, -40.0, 460.0, 960.0)


@lru_cache(maxsize=1)
def layout() -> dict:
    return json.loads((DIST / "layout.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=64)
def _layer(path: str, w: int, h: int) -> Image.Image:
    return Image.open(DIST / path).convert("RGBA").resize((w, h), Image.Resampling.LANCZOS)


def _paste(canvas: Image.Image, path: str, box: dict, scale: float) -> None:
    x, y = round((box["x"] - VIEW[0]) * scale), round((box["y"] - VIEW[1]) * scale)
    img = _layer(path, max(1, round(box["w"] * scale)), max(1, round(box["h"] * scale)))
    canvas.alpha_composite(img, (x, y)) if x >= 0 and y >= 0 else canvas.paste(img, (x, y), img)


def render_avatar(face_label: str, hair_label: str, body_label: str, height: int = 760) -> Image.Image:
    """합성 순서: 뒷머리 → 체형 → 얼굴(목 포함) → 얼굴 자체 머리 → 헤어."""
    L = layout()
    face, hair, body = FACES[face_label], HAIR[hair_label], BODIES[body_label]
    scale = height / VIEW[3]
    canvas = Image.new("RGBA", (round(VIEW[2] * scale), height), (248, 246, 241, 255))
    if hair and hair in L.get("hairBack", {}):
        _paste(canvas, f"hair/{hair}-back.png", L["hairBack"][hair], scale)
    _paste(canvas, f"bodies/{body}.png", L["bodies"][body], scale)
    _paste(canvas, f"faces/{face}.png", L["faces"][face], scale)
    _paste(canvas, f"faces/{face}-hair.png", L["faceHair"][face], scale)
    if hair:
        _paste(canvas, f"hair/{hair}.png", L["hair"][hair], scale)
    return canvas.convert("RGB")
