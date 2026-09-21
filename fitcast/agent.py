"""Tool calling 챗봇 에이전트."""

from datetime import date
from functools import lru_cache

from langchain.agents import create_agent

from fitcast.llm import get_llm
from fitcast.prompts import AGENT_SYSTEM_PROMPT
from fitcast.rag.style_guide import search_style_guide
from fitcast.tools import build_shop_links, get_weather, search_products

# 에이전트에 넘길 최근 대화 턴 수
MAX_HISTORY_MESSAGES = 12


@lru_cache(maxsize=4)
def _build_agent(today: str):
    """날짜가 바뀌면 시스템 프롬프트를 갱신해 에이전트 재생성."""
    return create_agent(
        model=get_llm(),
        tools=[get_weather, search_style_guide, build_shop_links, search_products],
        system_prompt=AGENT_SYSTEM_PROMPT.format(today=today),
    )


def _text_of(content) -> str:
    """Gradio·LangChain 메시지 content에서 텍스트만 추출."""
    if isinstance(content, str):
        return content
    parts = []
    for part in content or []:
        if isinstance(part, str):
            parts.append(part)
        elif isinstance(part, dict) and part.get("type") == "text":
            parts.append(part.get("text", ""))
    return "\n".join(parts)


def chat(message: str, history: list[dict]) -> str:
    """Gradio ChatInterface용 핸들러 (history가 곧 대화 메모리)."""
    messages = [
        {"role": m["role"], "content": _text_of(m["content"])}
        for m in history[-MAX_HISTORY_MESSAGES:]
        if m.get("role") in ("user", "assistant")
    ]
    messages.append({"role": "user", "content": message})
    agent = _build_agent(date.today().isoformat())
    result = agent.invoke({"messages": messages})
    # 마지막 메시지가 에이전트의 최종 답변
    return _text_of(result["messages"][-1].content)
