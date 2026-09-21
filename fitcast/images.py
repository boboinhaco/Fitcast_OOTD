"""상품 이미지 내려받기 공통 규칙 (AI 피팅·누끼가 같이 씀).

- 서버가 대신 내려받는 주소는 https + 허용 호스트(구글 쇼핑·네이버 쇼핑 CDN)만
- 옷장 카탈로그 사진(/static/catalog/)과 누끼 캐시(/cutouts/)는 서버 파일에서 바로 읽음
"""

from pathlib import Path
from urllib.parse import urlparse

import requests

from fitcast import config

MAX_IMAGE_BYTES = 8 * 1024 * 1024


class ImageFetchError(RuntimeError):
    """허용되지 않은 주소·내려받기 실패·너무 큰 파일."""


def allowed_image_url(url: str) -> bool:
    u = urlparse(url or "")
    host = (u.hostname or "").lower()
    return u.scheme == "https" and any(host == h or host.endswith("." + h) for h in config.TRYON_IMAGE_HOSTS)


def local_image(url: str) -> Path | None:
    for prefix, folder in (("/static/catalog/", config.CATALOG_DIR), ("/cutouts/", config.CUTOUT_CACHE_DIR)):
        if url.startswith(prefix):
            name = url[len(prefix):]
            if name and "/" not in name and ".." not in name and (folder / name).is_file():
                return folder / name
    return None


def fetch_image(url: str) -> bytes:
    """로컬 파일이면 읽고, 아니면 허용 호스트에서만 내려받음 (8MB 제한)."""
    local = local_image(url)
    if local:
        return local.read_bytes()
    if not allowed_image_url(url):
        raise ImageFetchError("허용되지 않은 상품 이미지 주소예요.")
    try:
        res = requests.get(url, timeout=config.HTTP_TIMEOUT, stream=True)
        res.raise_for_status()
        raw = res.raw.read(MAX_IMAGE_BYTES + 1, decode_content=True)
    except requests.RequestException as e:
        raise ImageFetchError("상품 이미지를 내려받지 못했어요.") from e
    if len(raw) > MAX_IMAGE_BYTES:
        raise ImageFetchError("상품 이미지가 너무 커요.")
    return raw
