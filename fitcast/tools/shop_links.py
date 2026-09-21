"""쇼핑 플랫폼 검색 링크 생성 Tool (크롤링 없이 URL만 생성)."""

from typing import Optional
from urllib.parse import quote

from langchain_core.tools import tool

from fitcast import config


def make_links(keyword: str, platforms: Optional[list[str]] = None) -> dict[str, str]:
    """키워드로 플랫폼별 검색 URL dict 생성."""
    encoded = quote(keyword.strip())
    targets = platforms or list(config.SHOP_SEARCH_URLS)
    return {
        name: config.SHOP_SEARCH_URLS[name].format(q=encoded)
        for name in targets
        if name in config.SHOP_SEARCH_URLS
    }


def links_to_markdown(keyword: str, platforms: Optional[list[str]] = None) -> str:
    """검색 링크들을 마크다운 한 줄로 변환."""
    links = make_links(keyword, platforms)
    return " · ".join(f"[{name}]({url})" for name, url in links.items())


@tool
def build_shop_links(keyword: str, platforms: Optional[list[str]] = None) -> str:
    """옷 검색 키워드로 쇼핑 플랫폼별 검색 링크를 만든다. 아이템을 추천할 때마다 호출한다.

    Args:
        keyword: 2~4단어 한국어 검색 키워드 (예: 린넨 롱 원피스)
        platforms: 무신사, 29CM, 지그재그, 에이블리, 테무, 쉬인 중 선택. 생략하면 전체.
    """
    md = links_to_markdown(keyword, platforms)
    return md or "지원하지 않는 플랫폼이에요."
