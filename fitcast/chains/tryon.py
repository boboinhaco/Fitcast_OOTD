"""코디 결과를 아바타 착용 이미지로 생성."""

import base64
import io
import os
from typing import Optional

import requests
from PIL import Image

from fitcast.schemas import OutfitSet

EDIT_URL = "https://api.openai.com/v1/images/edits"
IMAGE_MODEL = os.getenv("FITCAST_IMAGE_MODEL", "gpt-image-2")


def build_tryon_prompt(outfit: OutfitSet) -> str:
    """구조화된 코디를 이미지 생성용 지시문으로 변환."""
    items = [outfit.top, outfit.bottom, outfit.outer, outfit.shoes, outfit.accessory]
    lines = "\n".join(f"- {it.name} ({it.search_keyword})" for it in items if it)
    return (
        "첫 번째 이미지의 인물에게 아래 옷들을 입혀 줘.\n"
        f"{lines}\n"
        "추가 이미지가 있으면 그 옷의 디자인을 참고해.\n"
        "인물의 얼굴, 헤어, 체형, 포즈는 그대로 유지하고 "
        "소재 질감과 자연스러운 주름, 그림자를 표현해 줘. "
        "전신 세로 구도, 흰 배경, 텍스트나 로고는 넣지 마."
    )


def _to_png_bytes(img: Image.Image) -> bytes:
    """PIL 이미지를 PNG 바이트로 변환."""
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, format="PNG")
    return buf.getvalue()


def generate_tryon(
    avatar: Image.Image,
    outfit: OutfitSet,
    reference_urls: Optional[list[str]] = None,
) -> Image.Image:
    """아바타와 코디(선택: 상품 이미지 URL)로 착용 이미지 생성."""
    files = [("image[]", ("avatar.png", _to_png_bytes(avatar), "image/png"))]
    # 상품 썸네일이 있으면 참고 이미지로 최대 4장 추가
    for i, url in enumerate((reference_urls or [])[:4]):
        try:
            ref = Image.open(io.BytesIO(requests.get(url, timeout=15).content))
            files.append(("image[]", (f"ref{i}.png", _to_png_bytes(ref), "image/png")))
        except Exception:
            # 썸네일 하나 실패해도 생성은 계속 진행
            continue

    res = requests.post(
        EDIT_URL,
        headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
        files=files,
        data={
            "model": IMAGE_MODEL,
            "prompt": build_tryon_prompt(outfit),
            "size": "1024x1536",
            "quality": "medium",
        },
        timeout=300,
    )
    if res.status_code != 200:
        raise RuntimeError(f"이미지 생성 실패({res.status_code}): {res.text[:300]}")
    data = base64.b64decode(res.json()["data"][0]["b64_json"])
    return Image.open(io.BytesIO(data))