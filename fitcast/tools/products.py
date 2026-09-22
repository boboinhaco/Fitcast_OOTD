"""실제 상품 검색 Tool (SerpApi 구글 쇼핑 우선, 네이버 쇼핑 검색 API 대체)."""

import html
import re
from functools import lru_cache

import requests
from langchain_core.tools import tool

from fitcast import config

# 네이버: 패션 카테고리 결과를 우선으로 (가구·생활용품이 섞여 나오는 걸 막음)
FASHION_CATEGORIES = ("패션의류", "패션잡화")
TAG_RE = re.compile(r"<[^>]+>")
# 여성 사용자 서비스: 상품명에 남성·아동 표시가 있으면 제외
EXCLUDE_RE = re.compile(r"남성|남자|맨즈|멘즈|\bmen'?s?\b|\bman\b|보이즈|키즈|아동|주니어|유아|베이비", re.I)


class ProductSearchError(RuntimeError):
    """키 미설정·API 오류 (화면에서는 실제 상품 없이 기본 썸네일로 대체)."""


def provider() -> str:
    """사용할 검색 공급자: serpapi | naver | '' (키 없음)."""
    if config.SERPAPI_KEY:
        return "serpapi"
    if config.NAVER_CLIENT_ID and config.NAVER_CLIENT_SECRET:
        return "naver"
    return ""


def products_enabled() -> bool:
    return bool(provider())


def clean_title(title: str) -> str:
    """검색어 강조 태그(<b>)와 HTML 엔티티 제거."""
    return html.unescape(TAG_RE.sub("", title or "")).strip()


def from_naver(item: dict) -> dict:
    return {
        "name": clean_title(item.get("title", "")),
        "brand": item.get("brand") or item.get("maker") or item.get("mallName") or "",
        "mall": item.get("mallName", ""),
        "price": int(item.get("lprice") or 0),
        "image": item.get("image", ""),
        "link": item.get("link", ""),
    }


def from_serpapi(item: dict) -> dict:
    # 구글 쇼핑은 브랜드 필드가 없어 판매처를 브랜드 자리에 씀
    source = (item.get("source") or "").strip()
    return {
        "name": clean_title(item.get("title", "")),
        "brand": source,
        "mall": source,
        "price": int(item.get("extracted_price") or 0),
        "image": item.get("thumbnail") or item.get("serpapi_thumbnail") or "",
        "link": item.get("product_link") or item.get("link") or "",
    }


def _naver(keyword: str, display: int) -> list[dict]:
    res = requests.get(
        config.NAVER_SHOP_URL,
        params={"query": keyword, "display": display, "sort": "sim"},
        headers={"X-Naver-Client-Id": config.NAVER_CLIENT_ID, "X-Naver-Client-Secret": config.NAVER_CLIENT_SECRET},
        timeout=config.HTTP_TIMEOUT,
    )
    if res.status_code in (401, 403):
        raise ProductSearchError("네이버 API 키가 올바르지 않아요.")
    res.raise_for_status()
    items = res.json().get("items") or []
    fashion = [i for i in items if i.get("category1") in FASHION_CATEGORIES]
    return [from_naver(i) for i in (fashion or items)]


def _serpapi(keyword: str, display: int) -> list[dict]:
    res = requests.get(
        config.SERPAPI_URL,
        params={"engine": "google_shopping", "q": keyword, "gl": "kr", "hl": "ko", "api_key": config.SERPAPI_KEY},
        timeout=config.SERPAPI_TIMEOUT,
    )
    if res.status_code in (401, 403):
        raise ProductSearchError("SerpApi 키가 올바르지 않거나 사용량을 초과했어요.")
    res.raise_for_status()
    data = res.json()
    # 결과가 없으면 SerpApi가 error 필드로 알려줌 → 빈 목록으로 처리
    return [from_serpapi(i) for i in (data.get("shopping_results") or [])[: display * 3]]


def fallback_keywords(keyword: str) -> list[str]:
    """긴 키워드는 결과가 없을 때가 많아 앞 단어(주로 색)를 빼며 재시도."""
    words = keyword.split()
    out = [keyword]
    if len(words) >= 3:
        out.append(" ".join(words[1:]))
    if len(words) >= 2:
        out.append(" ".join(words[-2:]))
    return list(dict.fromkeys(out))


def relevance(keyword: str, name: str) -> int:
    """아이템 이름(마지막 단어, 예: 볼레로)이 상품명에 있으면 크게 가산, 나머지 단어는 조금씩."""
    words = keyword.split()
    title = name.replace(" ", "")
    return (3 if words and words[-1] in title else 0) + sum(1 for w in words[:-1] if w in title)


@lru_cache(maxsize=256)
def _search(keyword: str, display: int) -> tuple:
    """결과가 없거나 1위 상품에 아이템 이름이 없으면 더 짧은 키워드로 재검색해 더 나은 쪽을 고름."""
    search = _serpapi if provider() == "serpapi" else _naver
    best: list[dict] = []
    for kw in fallback_keywords(keyword):
        found = [p for p in search(kw, display) if p["image"] and p["name"]]
        found.sort(key=lambda p: -relevance(keyword, p["name"]))  # 같은 점수는 원래 순서 유지
        if found and (not best or relevance(keyword, found[0]["name"]) > relevance(keyword, best[0]["name"])):
            best = found
        if best and relevance(keyword, best[0]["name"]) >= 3:
            break
    return tuple(best[:display])


def is_excluded(name: str) -> bool:
    return bool(EXCLUDE_RE.search(name or ""))


def fetch_products(keyword: str, display: int = 5, female: bool = False) -> list[dict]:
    """키워드로 실제 상품 목록 조회 (같은 키워드는 캐시). female=True면 '여성 키워드'로 먼저 찾고 남성·아동 상품은 뺌."""
    keyword = (keyword or "").strip()
    if not keyword:
        return []
    if not products_enabled():
        raise ProductSearchError("상품 검색 키(SERPAPI_KEY 또는 NAVER_CLIENT_ID·SECRET)가 설정되지 않았어요.")
    try:
        n = max(1, min(display, 20))
        if female:
            found = [p for p in _search(f"여성 {keyword}", n) if not is_excluded(p["name"])]
            if len(found) >= 2:
                return found
            return [p for p in _search(keyword, n) if not is_excluded(p["name"])] or found
        return list(_search(keyword, n))
    except requests.RequestException as e:
        raise ProductSearchError(f"상품 검색 중 오류가 났어요: {e}") from e


def products_to_text(products: list[dict]) -> str:
    """LLM이 읽기 좋은 짧은 목록."""
    return "\n".join(f"- [{p['brand'] or p['mall']}] {p['name']} · {p['price']:,}원 · {p['link']}" for p in products)


@tool
def search_products(keyword: str) -> str:
    """실제 판매 중인 옷·신발·가방을 찾아야 할 때 호출한다. 판매처·상품명·가격·구매 링크를 돌려준다.

    Args:
        keyword: 2~3단어 한국어 검색 키워드 (예: 린넨 롱 스커트)
    """
    try:
        products = fetch_products(keyword, display=5)
    except ProductSearchError as e:
        return f"상품 검색을 할 수 없어요: {e} build_shop_links로 검색 링크를 대신 안내하세요."
    return products_to_text(products) or "검색 결과가 없어요. 키워드를 바꿔 다시 시도하세요."
