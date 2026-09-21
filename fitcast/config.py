"""환경변수와 고정 설정값 모음."""

import os
from pathlib import Path

from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 프로젝트 경로
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
WEB_DIR = ROOT_DIR / "web"
AVATAR_KIT_DIR = ROOT_DIR / "avatar_kit" / "dist"  # build_assets.py 결과물

# 모델 설정
MODEL_NAME = os.getenv("FITCAST_MODEL", "openai:gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("FITCAST_EMBEDDING_MODEL", "openai:text-embedding-3-small")
TEMPERATURE = os.getenv("FITCAST_TEMPERATURE", "").strip()

# 기본 도시
DEFAULT_CITY = os.getenv("FITCAST_DEFAULT_CITY", "서울")

# 외부 API 타임아웃(초)
HTTP_TIMEOUT = 10

# UI 선택지: 선호 스타일
STYLE_OPTIONS = [
    "캐주얼", "미니멀", "스트릿", "모리걸", "걸리시", "페미닌",
    "시티보이", "아메카지", "고프코어", "빈티지", "댄디", "스포티",
]

# UI 선택지: TPO(드레스코드)
TPO_OPTIONS = [
    "일상", "출근/오피스", "데이트", "여행", "운동/아웃도어",
    "결혼식 하객", "면접", "학교",
]

# UI 선택지: 성별 핏
GENDER_OPTIONS = ["여성", "남성", "상관없음"]

# 쇼핑 플랫폼 검색 URL 패턴 ({q}에 인코딩된 키워드가 들어감)
SHOP_SEARCH_URLS = {
    "무신사": "https://www.musinsa.com/search/goods?keyword={q}",
    "29CM": "https://www.29cm.co.kr/search?keyword={q}",
    "지그재그": "https://zigzag.kr/search?keyword={q}",
    "에이블리": "https://m.a-bly.com/search?keyword={q}",
    "테무": "https://www.temu.com/search_result.html?search_key={q}",
    "쉬인": "https://kr.shein.com/pdsearch/{q}",
}

# 아바타에 입힐 모양 코드 (web/js/avatar.js의 SHAPES와 이름을 맞춰야 함)
AVATAR_SHAPES = {
    "top": [
        "tee", "shirt", "blouse", "knit", "cami", "hoodie", "sweat",
        "crop", "jersey", "turtleneck", "polo", "sleeveless",
    ],
    "bottom": [
        "wide", "straight", "bootcut", "slacks", "cargo", "jogger", "shorts", "leggings",
        "mini", "pleats", "midi", "long_skirt", "slip_dress", "long_dress", "knit_dress",
    ],
    "outer": [
        "cardigan", "bolero", "blazer", "trench", "coat", "padding",
        "leather", "windbreaker", "jacket", "knit_vest",
    ],
    "shoes": [
        "sneakers", "loafers", "boots", "combat", "long_boots",
        "mules", "sandals", "maryjane", "flats", "heels",
    ],
    "accessory": [
        "bag_shoulder", "bag_tote", "bag_cross", "backpack", "cap", "beanie", "beret",
        "bucket", "sunglasses", "glasses", "necklace", "pearl", "chain", "scarf", "belt",
    ],
}
