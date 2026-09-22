"""AI 피팅: 아바타 이미지 + 실제 상품 이미지를 이미지 편집 모델에 보내 입힌 모습을 생성."""

import base64
import hashlib
import io
import os

from PIL import Image

from fitcast import config
from fitcast.images import MAX_IMAGE_BYTES, ImageFetchError, allowed_image_url, fetch_image, local_image  # noqa: F401 (테스트에서 참조)
from fitcast.prompts import TRYON_PROMPT

MAX_PRODUCTS = 6


class TryOnError(RuntimeError):
    """키 미설정·이미지 오류·생성 실패 (화면에는 안내 문구로 표시)."""


def decode_data_url(data_url: str) -> bytes:
    """'data:image/png;base64,...' → bytes."""
    head, _, body = (data_url or "").partition(",")
    if not head.startswith("data:image/") or ";base64" not in head:
        raise TryOnError("아바타 이미지 형식이 올바르지 않아요.")
    raw = base64.b64decode(body, validate=False)
    if len(raw) > MAX_IMAGE_BYTES:
        raise TryOnError("아바타 이미지가 너무 커요.")
    return raw


def to_png(raw: bytes, max_side: int = 1024) -> bytes:
    """모델 입력용 PNG로 정규화 (투명 배경은 흰색으로)."""
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as e:
        raise TryOnError("이미지를 읽지 못했어요.") from e
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.alpha_composite(img)
        img = bg
    img = img.convert("RGB")
    img.thumbnail((max_side, max_side))
    out = io.BytesIO()
    img.save(out, "PNG")
    return out.getvalue()


def fit_canvas(png: bytes, size: tuple[int, int] = (1024, 1536), fill: float = 0.9) -> bytes:
    """아바타를 출력과 같은 2:3 캔버스 가운데에 여백을 두고 배치 (모델이 머리·발을 잘라내지 않게)."""
    img = Image.open(io.BytesIO(png)).convert("RGB")
    scale = min(size[0] * fill / img.width, size[1] * fill / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (255, 255, 255))
    canvas.paste(img, ((size[0] - img.width) // 2, (size[1] - img.height) // 2))
    out = io.BytesIO()
    canvas.save(out, "PNG")
    return out.getvalue()


def download_product(url: str) -> bytes:
    try:
        return fetch_image(url)
    except ImageFetchError as e:
        raise TryOnError(str(e)) from e


def cache_key(avatar_png: bytes, products: list[dict], profile: dict | None = None) -> str:
    """같은 아바타·상품·프로필·모델·프롬프트면 같은 키 (시연용 결과 재사용)."""
    h = hashlib.sha256(avatar_png)
    for p in products:
        h.update(f"|{p.get('image', '')}|{p.get('name', '')}".encode())
    h.update(f"|{config.IMAGE_MODEL}|{TRYON_PROMPT}|{profile_text(profile)}".encode())
    return h.hexdigest()[:32]


def profile_text(profile: dict | None) -> str:
    """온보딩 프로필(키·몸무게·체형·헤어)을 프롬프트 한 문장으로."""
    if not profile:
        return ""
    bits = []
    if profile.get("height") and profile.get("weight"):
        bits.append(f"{profile['height']} cm tall and {profile['weight']} kg")
    if profile.get("body"):
        bits.append(f"{profile['body']} body shape")
    if profile.get("hair"):
        bits.append(f"{profile['hair']} hairstyle")
    if profile.get("face"):
        bits.append(f"{profile['face']} facial mood")
    if not bits:
        return ""
    return "The model is " + ", ".join(bits) + "; fit the garments to this body and keep this hairstyle."


def build_prompt(products: list[dict], profile: dict | None = None) -> str:
    items = "; ".join(f"image {i + 2}: {p.get('label') or ''} {p.get('name') or 'item'}".strip() for i, p in enumerate(products))
    return TRYON_PROMPT.format(items=items, profile=profile_text(profile))


def generate_tryon(avatar_data_url: str, products: list[dict], profile: dict | None = None) -> dict:
    """아바타(data URL)와 상품 목록[{image, name, label}], 프로필(키·몸무게·체형·헤어)로 입힌 이미지를 생성해 PNG data URL 반환."""
    products = [p for p in products if p.get("image")][:MAX_PRODUCTS]
    if not products:
        raise TryOnError("실제 상품 이미지가 있는 아이템이 하나 이상 필요해요.")
    avatar_png = fit_canvas(to_png(decode_data_url(avatar_data_url), max_side=1536))
    key = cache_key(avatar_png, products, profile)
    cached = config.TRYON_CACHE_DIR / f"{key}.png"
    if cached.exists():
        return {"image": "data:image/png;base64," + base64.b64encode(cached.read_bytes()).decode(), "cached": True, "key": key}

    if not os.getenv("OPENAI_API_KEY"):
        raise TryOnError("OPENAI_API_KEY가 설정되지 않았어요.")
    from openai import OpenAI  # 키가 있을 때만 로드

    files = [("avatar.png", avatar_png, "image/png")]
    files += [(f"product{i}.png", to_png(download_product(p["image"])), "image/png") for i, p in enumerate(products)]
    try:
        result = OpenAI().images.edit(
            model=config.IMAGE_MODEL, image=files, prompt=build_prompt(products, profile), size="1024x1536", n=1,
        )
        b64 = result.data[0].b64_json
    except Exception as e:  # 모델·네트워크 오류는 화면에 안내만 하고 핵심 기능은 그대로
        raise TryOnError(f"AI 피팅 생성에 실패했어요: {e}") from e
    if not b64:
        raise TryOnError("AI 피팅 결과가 비어 있어요.")

    config.TRYON_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(base64.b64decode(b64))
    return {"image": "data:image/png;base64," + b64, "cached": False, "key": key}
