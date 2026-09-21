"""상품 사진 누끼(배경 제거)와 '옷만 찍힌 사진' 고르기.

- remove_background: rembg(u2net)로 배경을 지움. rembg가 없으면 흰 배경만 걷어내는 간단한 방식으로 대체
- product_only_flags: 비전 모델(OpenAI)에게 후보 썸네일 격자를 보여주고 '사람 없이 상품만 찍힌 사진'을 고르게 함
- garment_score: 비전 모델을 못 쓸 때의 대체 점수 (살색이 많거나 세로로 긴 전신컷은 감점)
- cutout_for_url: 상품 이미지 URL → 누끼 PNG 파일 (data/cutout_cache/에 캐시, 화면은 /cutouts/로 접근)
- rank_products: 검색 결과를 상품컷 우선으로 정렬하고 누끼 정보를 붙임 (AI 코디 아이템을 아바타에 입힐 때)
"""

import base64
import hashlib
import io
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from fitcast import config
from fitcast.images import ImageFetchError, fetch_image

MAX_SIDE = 512
TILE = 224
JUDGE_PROMPT = (
    "This is a grid of {n} numbered product thumbnails (the number is drawn at the top-left of each tile; "
    "tiles are ordered left to right, top to bottom, starting at 1). "
    "Return JSON {{\"product_only\": [numbers]}} listing every tile that shows ONLY the product itself "
    "(clothing, shoes, bag, hat, glasses, jewelry, belt) photographed flat, on a hanger or on a plain background. "
    "A tile qualifies only if NO part of a human body is visible at all: no face, hair, neck, hands, arms, legs, feet, torso, "
    "and no mannequin. A garment worn on a body, even cropped so only legs or a torso show, does NOT qualify. "
    "Return an empty list if none qualify."
)
_session = None


class CutoutError(RuntimeError):
    """내려받기·처리 실패 (화면은 벡터 옷으로 대체)."""


def _rembg():
    """rembg 세션 (첫 호출 때 모델 로드, 없으면 None)."""
    global _session
    if _session is None:
        try:
            from rembg import new_session  # 무거워서 필요할 때만 로드

            _session = new_session("u2net")
        except Exception:  # 미설치·모델 내려받기 실패
            _session = False
    return _session or None


def _white_bg_alpha(img: Image.Image) -> Image.Image:
    """rembg가 없을 때: 테두리와 이어진 밝은 배경만 투명하게."""
    arr = np.asarray(img.convert("RGB"), dtype=np.int16)
    light = (arr.min(2) > 235) & (arr.max(2) - arr.min(2) < 14)
    reach = np.zeros_like(light)
    reach[[0, -1], :] = light[[0, -1], :]
    reach[:, [0, -1]] = light[:, [0, -1]]
    while True:
        grown = reach.copy()
        grown[1:] |= reach[:-1]
        grown[:-1] |= reach[1:]
        grown[:, 1:] |= reach[:, :-1]
        grown[:, :-1] |= reach[:, 1:]
        grown &= light
        if np.array_equal(grown, reach):
            break
        reach = grown
    alpha = Image.fromarray(((~reach) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
    out = img.convert("RGBA")
    out.putalpha(alpha)
    return out


def remove_background(raw: bytes) -> Image.Image:
    """이미지 bytes → 배경이 투명한 RGBA."""
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as e:
        raise CutoutError("이미지를 읽지 못했어요.") from e
    session = _rembg()
    if session is None:
        return _white_bg_alpha(img)
    from rembg import remove

    return remove(img.convert("RGBA"), session=session, post_process_mask=True).convert("RGBA")


def trim(img: Image.Image, pad: float = 0.03, max_side: int = MAX_SIDE) -> Image.Image:
    """알파 bbox로 자르고 여백을 조금 두고, 긴 변을 max_side 이하로."""
    box = img.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    if box:
        x0, y0, x1, y1 = box
        p = int(max(x1 - x0, y1 - y0) * pad)
        img = img.crop((max(0, x0 - p), max(0, y0 - p), min(img.width, x1 + p), min(img.height, y1 + p)))
    if max(img.size) > max_side:
        img = img.copy()
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return img


def skin_ratio(img: Image.Image) -> float:
    """불투명 픽셀 중 살색 비율 (YCbCr 범위). 모델 착용컷 걸러내기용."""
    arr = np.asarray(img.convert("RGBA"), dtype=np.float32)
    a = arr[..., 3] > 128
    if a.sum() < 50:
        return 0.0
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    cb = 128 - 0.1687 * r - 0.3313 * g + 0.5 * b
    cr = 128 + 0.5 * r - 0.4187 * g - 0.0813 * b
    skin = (cb > 80) & (cb < 120) & (cr > 136) & (cr < 168) & (r > g) & (g > b) & (r > 95)
    return float((skin & a).sum() / a.sum())


def garment_score(img: Image.Image) -> float:
    """옷만 찍힌 사진일수록 높은 점수 (살색이 많거나 세로로 긴 전신컷은 감점)."""
    alpha = np.asarray(img.getchannel("A")) > 128
    if alpha.sum() < 50:
        return -5.0
    rows = np.flatnonzero(alpha.any(1))
    cols = np.flatnonzero(alpha.any(0))
    h, w = rows[-1] - rows[0] + 1, cols[-1] - cols[0] + 1
    widths = alpha[rows[0] : rows[-1] + 1].sum(1)
    head = widths[: max(1, h // 8)].mean() / max(1, widths.max())  # 위쪽이 좁으면 머리(사람)
    skin = skin_ratio(img)
    score = -8 * min(skin, 0.5)
    if skin > 0.04 and head < 0.45:
        score -= 2
    if h / w > 1.8:
        score -= 1.5
    if alpha.sum() / alpha.size < 0.06:
        score -= 1
    return score


def tile_sheet(images: list[bytes]) -> bytes:
    """후보 썸네일을 번호 붙인 격자 JPEG 하나로 (비전 모델 호출 1번으로 전부 판정)."""
    cols = min(4, len(images))
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * TILE, rows * TILE), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=30)
    except Exception:
        font = ImageFont.load_default()
    for i, raw in enumerate(images):
        x, y = (i % cols) * TILE, (i // cols) * TILE
        try:
            im = Image.open(io.BytesIO(raw)).convert("RGB")
            im.thumbnail((TILE - 8, TILE - 8))
            sheet.paste(im, (x + (TILE - im.width) // 2, y + (TILE - im.height) // 2))
        except Exception:
            pass
        draw.rectangle([x, y, x + 40, y + 36], fill="black")
        draw.text((x + 6, y + 2), str(i + 1), fill="white", font=font)
    out = io.BytesIO()
    sheet.save(out, "JPEG", quality=85)
    return out.getvalue()


def product_only_flags(images: list[bytes]) -> list[bool] | None:
    """비전 모델에게 '사람 없이 상품만 찍힌 사진' 번호를 받아 플래그로. 키가 없거나 실패하면 None."""
    if not images or not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from openai import OpenAI

        data_url = "data:image/jpeg;base64," + base64.b64encode(tile_sheet(images)).decode()
        res = OpenAI().chat.completions.create(
            model=config.VISION_MODEL,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": [
                {"type": "text", "text": JUDGE_PROMPT.format(n=len(images))},
                {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
            ]}],
            max_tokens=100,
        )
        picked = json.loads(res.choices[0].message.content or "{}").get("product_only") or []
        picked = {int(v) for v in picked if str(v).isdigit()}
    except Exception:
        return None
    return [(i + 1) in picked for i in range(len(images))]


def photo_anchors(img: Image.Image) -> dict:
    """누끼 사진의 기준폭 (이미지 폭 대비 비율). 아바타 골격 치수에 맞춰 사진 크기를 정할 때 씀.

    top: 위쪽 25% 구간의 최대 폭 (상의·아우터·원피스의 어깨선), waist: 위쪽 10% 구간의 최대 폭 (하의 허리선), max: 전체 최대 폭
    """
    alpha = np.asarray(img.getchannel("A")) > 64
    rows = np.flatnonzero(alpha.any(1))
    if not len(rows):
        return {"top": 1.0, "waist": 1.0, "max": 1.0}
    widths = []
    for y in range(rows[0], rows[-1] + 1):
        xs = np.flatnonzero(alpha[y])
        widths.append(xs[-1] - xs[0] + 1 if len(xs) else 0)
    widths = np.array(widths, dtype=np.float32)
    h, w = len(widths), img.width
    part = lambda frac: float(widths[: max(1, int(h * frac))].max() / w)
    return {"top": round(part(0.25), 3), "waist": round(part(0.10), 3), "max": round(float(widths.max() / w), 3)}


def cache_path(url: str) -> Path:
    return config.CUTOUT_CACHE_DIR / (hashlib.sha1(url.encode()).hexdigest()[:24] + ".png")


def download(url: str) -> bytes:
    try:
        return fetch_image(url)
    except ImageFetchError as e:
        raise CutoutError(str(e)) from e


def cutout_for_url(url: str, raw: bytes | None = None) -> dict:
    """상품 이미지 URL → {"image": "/cutouts/<id>.png", "w", "h"} (캐시 있으면 바로)."""
    path = cache_path(url)
    if not path.exists():
        img = trim(remove_background(raw or download(url)))
        config.CUTOUT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        img.save(path, optimize=True)
    with Image.open(path) as im:
        return {"image": f"/cutouts/{path.name}", "w": im.width, "h": im.height, **photo_anchors(im.convert("RGBA"))}


def _safe_download(url: str) -> bytes | None:
    try:
        return download(url)
    except CutoutError:
        return None


def _score_cutout(cut: dict) -> float:
    with Image.open(config.CUTOUT_CACHE_DIR / Path(cut["image"]).name) as im:
        return garment_score(im.convert("RGBA"))


def rank_products(items: list[dict], limit: int = 6) -> list[dict]:
    """검색 결과를 '상품만 찍힌 사진' 우선으로 정렬하고, 그 사진들에는 누끼 정보를 붙임.

    비전 판정을 못 쓰면 누끼 모양 점수(garment_score)로 대신 고른다. 착용컷은 누끼 없이 뒤로 (아바타엔 벡터 옷 유지).
    """
    head = items[:limit]
    with ThreadPoolExecutor(4) as ex:
        raws = list(ex.map(lambda p: _safe_download(p["image"]), head))
    got = [(i, p, raw) for i, (p, raw) in enumerate(zip(head, raws)) if raw]
    flags = product_only_flags([raw for _, _, raw in got])
    ranked = [(-9.0, i, p) for i, (p, raw) in enumerate(zip(head, raws)) if not raw]
    for k, (i, p, raw) in enumerate(got):
        try:
            if flags is None:  # 판정 없이: 누끼 모양 점수로
                cut = cutout_for_url(p["image"], raw)
                score = _score_cutout(cut)
                ranked.append((score, i, {**p, "cutout": cut} if score > -2 else p))
            elif flags[k]:
                ranked.append((5.0, i, {**p, "cutout": cutout_for_url(p["image"], raw)}))
            else:
                ranked.append((-1.0, i, p))
        except CutoutError:
            ranked.append((-9.0, i, p))
    ranked.sort(key=lambda t: (-t[0], t[1]))
    return [p for _, _, p in ranked] + items[limit:]
