"""스타일 가이드 미니 RAG (문서 로드 → 분할 → 임베딩 → 검색)."""

import json
from functools import lru_cache

from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import MarkdownHeaderTextSplitter

from fitcast import config
from fitcast.llm import get_embeddings

STYLE_GUIDE_PATH = config.DATA_DIR / "style_guide.md"
TEMP_GUIDE_PATH = config.DATA_DIR / "temp_guide.json"


def load_style_docs():
    """마크다운을 '## 섹션' 단위 Document로 분할."""
    text = STYLE_GUIDE_PATH.read_text(encoding="utf-8")
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("##", "section")],
        strip_headers=False,
    )
    # 제목(#)만 있는 머리말 조각은 제외
    return [d for d in splitter.split_text(text) if d.metadata.get("section")]


@lru_cache(maxsize=1)
def get_vectorstore() -> InMemoryVectorStore:
    """벡터스토어를 앱 시작 후 한 번만 생성."""
    return InMemoryVectorStore.from_documents(load_style_docs(), get_embeddings())


def retrieve_style_context(query: str, k: int = 3) -> str:
    """질의와 가까운 스타일 가이드 조각을 합쳐 문자열로 반환."""
    docs = get_vectorstore().similarity_search(query, k=k)
    return "\n\n".join(d.page_content for d in docs)


@lru_cache(maxsize=1)
def _temp_bands() -> list[dict]:
    """기온 구간표 로드."""
    return json.loads(TEMP_GUIDE_PATH.read_text(encoding="utf-8"))


def temp_band_guide(temp_avg: float) -> str:
    """평균 기온에 해당하는 구간 가이드를 문자열로 반환(규칙 기반)."""
    # 높은 구간부터 내려오며 처음 걸리는 구간 선택
    for band in sorted(_temp_bands(), key=lambda b: b["min"], reverse=True):
        if temp_avg >= band["min"]:
            return f"{band['label']}: 대표 아이템 {', '.join(band['items'])}. {band['tip']}"
    return "해당 기온 구간 가이드 없음"


@tool
def search_style_guide(query: str) -> str:
    """스타일(모리걸, 미니멀 등)·TPO·날씨 보정 규칙에 대한 내부 가이드를 검색한다.

    Args:
        query: 검색 질의 (예: '모리걸 더운 날', '결혼식 하객 주의점')
    """
    return retrieve_style_context(query)
