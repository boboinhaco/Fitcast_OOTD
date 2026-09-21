"""구조화 출력용 Pydantic 스키마."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class OutfitItem(BaseModel):
    """코디를 구성하는 아이템 하나."""

    name: str = Field(description="아이템 이름 (예: 린넨 롱 원피스)")
    reason: str = Field(description="이 날씨·스타일에 이 아이템을 고른 이유 한 문장")
    search_keyword: str = Field(description="쇼핑 검색에 쓸 짧은 2~3단어 한국어 키워드 (색 + 아이템)")
    shape: str = Field(default="", description="아바타에 입힐 모양 코드. 프롬프트의 부위별 목록에서만 고른다")
    color_hex: str = Field(default="#8a8a8a", description="아이템 대표 색상 HEX 코드 (예: #1f2a44)")


class OutfitSet(BaseModel):
    """날씨와 취향에 맞춘 코디 한 세트."""

    summary: str = Field(description="오늘 코디 컨셉 한 줄 요약")
    top: OutfitItem = Field(description="상의")
    bottom: OutfitItem = Field(description="하의 (원피스면 원피스를 여기에)")
    outer: Optional[OutfitItem] = Field(default=None, description="외투 (필요 없으면 null)")
    shoes: OutfitItem = Field(description="신발")
    accessory: Optional[OutfitItem] = Field(default=None, description="악세사리·가방·우산 등")
    weather_tip: str = Field(description="비·일교차·자외선 등 날씨 관련 주의사항 한 문장")


class DetectedClothing(BaseModel):
    """사진에서 찾아낸 옷 한 벌."""

    category: Literal["상의", "하의", "원피스", "외투", "신발", "악세사리", "기타"]
    description: str = Field(description="색·소재·핏·디테일을 담은 묘사")
    brand_guess: Optional[str] = Field(default=None, description="로고 등 근거가 있을 때만 브랜드 추정")
    brand_confidence: Literal["높음", "보통", "낮음", "알 수 없음"] = "알 수 없음"
    search_keyword: str = Field(description="비슷한 옷을 찾기 위한 2~4단어 한국어 키워드")


class ClothingAnalysis(BaseModel):
    """사진 분석 결과 전체."""

    items: list[DetectedClothing] = Field(description="사진에서 식별한 옷 목록")
    style_tags: list[str] = Field(description="전체 스타일 태그 (예: 미니멀, 스트릿)")
    matching_tips: list[str] = Field(description="이 옷과 매칭하면 좋은 아이템 제안 2~4개")
