"""LLM·임베딩 모델 생성기."""

from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings

from fitcast import config


@lru_cache(maxsize=1)
def get_llm():
    """챗 모델을 한 번만 만들어 재사용."""
    kwargs = {}
    # 온도값이 설정된 경우에만 전달
    if config.TEMPERATURE:
        kwargs["temperature"] = float(config.TEMPERATURE)
    return init_chat_model(config.MODEL_NAME, **kwargs)


@lru_cache(maxsize=1)
def get_embeddings():
    """임베딩 모델을 한 번만 만들어 재사용."""
    return init_embeddings(config.EMBEDDING_MODEL)
