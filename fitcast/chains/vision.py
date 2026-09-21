"""사진 속 옷 분석 체인 (멀티모달 메시지 + 구조화 출력)."""

import base64
import io
from typing import Optional

from langchain_core.messages import HumanMessage
from PIL import Image

from fitcast.llm import get_llm
from fitcast.prompts import VISION_INSTRUCTION
from fitcast.schemas import ClothingAnalysis
from fitcast.tools.shop_links import links_to_markdown

# 전송 전 이미지 최대 변 길이(px)
MAX_SIDE = 1024


def _to_data_url(image: Image.Image) -> str:
    """PIL 이미지를 축소해 base64 data URL로 변환."""
    img = image.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def analyze_clothing(image: Image.Image) -> ClothingAnalysis:
    """이미지를 LLM에 보내 ClothingAnalysis로 받기."""
    message = HumanMessage(content=[
        {"type": "text", "text": VISION_INSTRUCTION},
        {"type": "image_url", "image_url": {"url": _to_data_url(image)}},
    ])
    return get_llm().with_structured_output(ClothingAnalysis).invoke([message])


def analysis_to_markdown(result: ClothingAnalysis, platforms: Optional[list[str]] = None) -> str:
    """분석 결과를 화면용 마크다운으로 변환."""
    lines = [f"**스타일 태그:** {' · '.join(result.style_tags)}"]
    for item in result.items:
        brand = (
            f"{item.brand_guess} (확신도: {item.brand_confidence})"
            if item.brand_guess else "사진만으로는 알기 어려워요"
        )
        lines.append(
            f"### {item.category}\n"
            f"{item.description}\n\n"
            f"- 브랜드 추정: {brand}\n"
            f"- 비슷한 옷 찾기 `{item.search_keyword}` → "
            f"{links_to_markdown(item.search_keyword, platforms)}"
        )
    tips = "\n".join(f"- {t}" for t in result.matching_tips)
    lines.append(f"### 이렇게 매칭해 보세요\n{tips}")
    return "\n\n".join(lines)
