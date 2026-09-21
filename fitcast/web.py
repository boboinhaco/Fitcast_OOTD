"""웹 프론트(랜딩·아바타 피팅룸) 서빙과 JSON API."""

from datetime import date, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from fitcast import config
from fitcast.chains.outfit import recommend_outfit
from fitcast.schemas import OutfitItem
from fitcast.tools.shop_links import make_links
from fitcast.tools.weather import format_weather

# 코디 슬롯 → 화면 라벨
SLOT_LABELS = {"top": "상의", "bottom": "하의", "outer": "외투", "shoes": "신발", "accessory": "악세사리"}


class Profile(BaseModel):
    """온보딩에서 고른 아바타 정보."""

    gender: str = "female"
    body: str = ""
    styles: list[str] = Field(default_factory=list)
    hair: str = ""
    face: str = ""
    height: int = Field(default=165, ge=120, le=220)
    weight: int = Field(default=55, ge=30, le=200)


class RecommendRequest(BaseModel):
    """AI 날씨 코디 요청."""

    city: str = Field(min_length=1)
    day: int = Field(default=0, ge=0, le=2)
    tpo: str = "일상"
    note: str = ""
    profile: Profile = Field(default_factory=Profile)


def profile_to_text(p: Profile) -> str:
    """프로필을 프롬프트용 한 줄로 변환."""
    bmi = p.weight / (p.height / 100) ** 2
    parts = [f"{p.height}cm / {p.weight}kg (BMI {bmi:.1f})"]
    if p.body:
        parts.append(f"체형 {p.body}")
    if p.hair:
        parts.append(f"헤어 {p.hair}")
    if p.face:
        parts.append(f"얼굴 분위기 {p.face}")
    return ", ".join(parts)


def _item_json(slot: str, item: OutfitItem) -> dict:
    """아이템 하나를 프론트용 dict로 변환."""
    return {
        "slot": slot,
        "label": SLOT_LABELS[slot],
        "name": item.name,
        "reason": item.reason,
        "keyword": item.search_keyword,
        "shape": item.shape,
        "color": item.color_hex,
        "links": make_links(item.search_keyword),
    }


def create_app() -> FastAPI:
    """정적 프론트와 API를 가진 FastAPI 앱 생성."""
    app = FastAPI(title="Fitcast")

    @app.get("/api/config")
    def get_config() -> dict:
        """프론트가 쓰는 선택지와 쇼핑 URL 패턴."""
        return {
            "default_city": config.DEFAULT_CITY,
            "tpo_options": config.TPO_OPTIONS,
            "shop_urls": config.SHOP_SEARCH_URLS,
        }

    @app.post("/api/recommend")
    def recommend(req: RecommendRequest) -> dict:
        """프로필·날씨 기반 코디 추천 (동기 함수라 스레드풀에서 실행됨)."""
        p = req.profile
        gender = {"female": "여성", "male": "남성"}.get(p.gender, "상관없음")
        target = date.today() + timedelta(days=req.day)
        try:
            result = recommend_outfit(
                city=req.city.strip(), styles=p.styles, tpo=req.tpo, gender=gender,
                note=req.note, date=target.isoformat(), profile=profile_to_text(p),
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"추천 중 문제가 생겼어요: {e}")

        outfit = result["outfit"]
        slots = {
            "top": outfit.top, "bottom": outfit.bottom, "outer": outfit.outer,
            "shoes": outfit.shoes, "accessory": outfit.accessory,
        }
        return {
            "weather": format_weather(result["weather_data"]),
            "summary": outfit.summary,
            "weather_tip": outfit.weather_tip,
            "items": [_item_json(slot, item) for slot, item in slots.items() if item],
        }

    app.mount("/static", StaticFiles(directory=config.WEB_DIR), name="static")
    app.mount("/avatar-kit", StaticFiles(directory=config.AVATAR_KIT_DIR), name="avatar-kit")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(config.WEB_DIR / "index.html")

    return app
