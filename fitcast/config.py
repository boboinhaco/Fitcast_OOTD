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

# 실제 상품 검색: SerpApi(구글 쇼핑) 우선, 없으면 네이버 쇼핑 검색 API. 둘 다 비면 기본 썸네일 사용
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()
SERPAPI_URL = "https://serpapi.com/search.json"
SERPAPI_TIMEOUT = 60  # 구글 쇼핑은 캐시가 없으면 20~30초 걸림
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "").strip()
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "").strip()
NAVER_SHOP_URL = "https://openapi.naver.com/v1/search/shop.json"

# AI 피팅(이미지 편집) 설정
IMAGE_MODEL = os.getenv("FITCAST_IMAGE_MODEL", "gpt-image-1").strip()
VISION_MODEL = os.getenv("FITCAST_VISION_MODEL", "gpt-4o").strip()  # 상품 사진에서 착용컷 걸러내는 판정용 (mini는 타일 번호를 자주 틀림)
TRYON_CACHE_DIR = DATA_DIR / "tryon_cache"  # 같은 입력이면 저장된 결과를 재사용 (시연용)
# 서버가 내려받아도 되는 상품 이미지 호스트 (구글 쇼핑·SerpApi·네이버 쇼핑 이미지)
TRYON_IMAGE_HOSTS = ("gstatic.com", "serpapi.com", "pstatic.net", "naver.net")

# 실제 상품 사진 누끼
CUTOUT_CACHE_DIR = DATA_DIR / "cutout_cache"  # 검색 결과 이미지의 누끼 (화면은 /cutouts/ 경로로 읽음)
CATALOG_DIR = WEB_DIR / "catalog"  # 옷장 카탈로그 상품 사진 (tools/build_catalog.py 결과물)

# 회원·저장한 코디 (SQLite)
DB_PATH = DATA_DIR / "fitcast.db"

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
