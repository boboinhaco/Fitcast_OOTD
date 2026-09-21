"""코디 세트 추천 체인 (LCEL + 구조화 출력)."""

from functools import lru_cache
from typing import Optional

from langchain_core.runnables import RunnablePassthrough

from fitcast import config
from fitcast.llm import get_llm
from fitcast.prompts import OUTFIT_PROMPT
from fitcast.rag.style_guide import retrieve_style_context, temp_band_guide
from fitcast.schemas import OutfitItem, OutfitSet
from fitcast.tools.shop_links import links_to_markdown
from fitcast.tools.weather import fetch_weather, format_weather


def _style_query(x: dict) -> str:
    """RAG 검색용 질의 문장 생성."""
    temp = x["weather_data"]["temp_avg"]
    feel = "더운 날" if temp >= 23 else "추운 날" if temp < 12 else "선선한 날"
    return f"{x['styles']} {feel} / TPO: {x['tpo']} / 날씨 보정 규칙"


def shape_guide() -> str:
    """프롬프트에 넣을 부위별 아바타 모양 코드 목록."""
    return "\n".join(f"- {part}: {', '.join(codes)}" for part, codes in config.AVATAR_SHAPES.items())


@lru_cache(maxsize=1)
def build_outfit_chain():
    """입력 dict → 날씨 조회 → 가이드 수집(병렬) → 프롬프트 → OutfitSet."""
    structured_llm = get_llm().with_structured_output(OutfitSet)
    return (
        # 1단계: 날씨 API 호출
        RunnablePassthrough.assign(
            weather_data=lambda x: fetch_weather(x["city"], x.get("date")),
        )
        # 2단계: 프롬프트 재료 세 가지를 병렬로 준비
        | RunnablePassthrough.assign(
            weather=lambda x: format_weather(x["weather_data"]),
            temp_guide=lambda x: temp_band_guide(x["weather_data"]["temp_avg"]),
            style_context=lambda x: retrieve_style_context(_style_query(x)),
        )
        # 3단계: LLM 호출 결과를 outfit 키에 추가
        | RunnablePassthrough.assign(outfit=OUTFIT_PROMPT | structured_llm)
    )


def recommend_outfit(
    city: str,
    styles: list[str],
    tpo: str,
    gender: str = "상관없음",
    note: str = "",
    date: Optional[str] = None,
    profile: str = "",
) -> dict:
    """UI에서 호출하는 진입 함수. weather_data와 outfit이 담긴 dict 반환."""
    return build_outfit_chain().invoke({
        "city": city,
        "date": date or None,
        "styles": ", ".join(styles) if styles else "특별한 선호 없음",
        "tpo": tpo or "일상",
        "gender": gender,
        "note": note or "없음",
        "profile": profile or "정보 없음",
        "shape_guide": shape_guide(),
    })


def _item_block(label: str, item: Optional[OutfitItem], platforms: Optional[list[str]]) -> str:
    """아이템 하나를 마크다운 블록으로 변환."""
    if item is None:
        return ""
    return (
        f"### {label} · {item.name}\n"
        f"{item.reason}\n\n"
        f"🔎 `{item.search_keyword}` → {links_to_markdown(item.search_keyword, platforms)}\n"
    )


def outfit_to_markdown(result: dict, platforms: Optional[list[str]] = None) -> str:
    """체인 결과를 화면에 뿌릴 마크다운으로 변환."""
    outfit: OutfitSet = result["outfit"]
    blocks = [
        f"**{format_weather(result['weather_data'])}**",
        f"## 👗 {outfit.summary}",
        _item_block("상의", outfit.top, platforms),
        _item_block("하의", outfit.bottom, platforms),
        _item_block("외투", outfit.outer, platforms),
        _item_block("신발", outfit.shoes, platforms),
        _item_block("악세사리", outfit.accessory, platforms),
        f"> ☂️ {outfit.weather_tip}",
    ]
    return "\n\n".join(b for b in blocks if b)
