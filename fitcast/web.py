"""웹 프론트(랜딩·아바타 피팅룸) 서빙과 JSON API."""

from datetime import date, timedelta

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from fitcast import accounts, config
from fitcast.chains.outfit import recommend_outfit
from fitcast.cutout import CutoutError, cutout_for_url, rank_products
from fitcast.schemas import OutfitItem
from fitcast.tools.products import ProductSearchError, fetch_products, products_enabled
from fitcast.tools.shop_links import make_links
from fitcast.tryon import TryOnError, generate_tryon
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


class TryOnProduct(BaseModel):
    """AI 피팅에 넣을 상품 한 개."""

    image: str
    name: str = ""
    label: str = ""


class TryOnRequest(BaseModel):
    """아바타 PNG(data URL) + 입힐 실제 상품들."""

    avatar: str = Field(min_length=32)
    products: list[TryOnProduct] = Field(default_factory=list, max_length=6)
    profile: dict = Field(default_factory=dict)  # 키·몸무게·체형·헤어 (프롬프트에 반영)


class SignupRequest(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=30)
    profile: dict = Field(default_factory=dict)


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileUpdate(BaseModel):
    profile: dict


class LookRequest(BaseModel):
    """저장할 코디: 착용 아이템·실제 상품·AI 피팅 이미지 키."""

    title: str = ""
    outfit: dict = Field(default_factory=dict)
    products: list[dict] = Field(default_factory=list)
    tryon_key: str = Field(default="", pattern=r"^[0-9a-f]{0,64}$")


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
            "products_enabled": products_enabled(),
        }

    @app.get("/api/products")
    def products(q: str, n: int = 5, cut: int = 0, female: int = 0) -> dict:
        """키워드로 실제 상품 검색 (SerpApi 구글 쇼핑 → 네이버). female=1이면 여성 상품 우선, cut=1이면 누끼를 떠서 옷만 찍힌 사진 순으로 정렬."""
        try:
            items = fetch_products(q, n, female=bool(female))
        except ProductSearchError as e:
            return {"enabled": products_enabled(), "items": [], "error": str(e)}
        if cut:
            items = rank_products(items, limit=n)
        return {"enabled": True, "items": items, "error": None}

    @app.get("/api/cutout")
    def cutout(url: str) -> dict:
        """상품 이미지 URL의 누끼 PNG 경로와 크기 (아바타에 종이인형처럼 올릴 때 사용)."""
        try:
            return cutout_for_url(url)
        except CutoutError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/tryon")
    def tryon(req: TryOnRequest) -> dict:
        """AI 피팅 보기: 이미지 편집 모델로 아바타에 실제 상품을 입힌 이미지 생성."""
        try:
            return generate_tryon(req.avatar, [p.model_dump() for p in req.products], req.profile)
        except TryOnError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ── 회원 · 저장한 코디 ──
    def set_session(res: Response, token: str) -> None:
        res.set_cookie(accounts.COOKIE, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)

    def need_user(token: str | None) -> dict:
        user = accounts.current_user(token)
        if not user:
            raise HTTPException(status_code=401, detail="로그인이 필요해요.")
        return user

    @app.post("/api/auth/signup")
    def signup(req: SignupRequest, res: Response) -> dict:
        try:
            user, token = accounts.signup(req.email, req.password, req.name, req.profile)
        except accounts.AccountError as e:
            raise HTTPException(status_code=400, detail=str(e))
        set_session(res, token)
        return {"user": user}

    @app.post("/api/auth/login")
    def login(req: LoginRequest, res: Response) -> dict:
        try:
            user, token = accounts.login(req.email, req.password)
        except accounts.AccountError as e:
            raise HTTPException(status_code=400, detail=str(e))
        set_session(res, token)
        return {"user": user}

    @app.post("/api/auth/logout")
    def logout(res: Response, fc_session: str | None = Cookie(default=None)) -> dict:
        if fc_session:
            accounts.logout(fc_session)
        res.delete_cookie(accounts.COOKIE)
        return {"ok": True}

    @app.get("/api/auth/me")
    def me(fc_session: str | None = Cookie(default=None)) -> dict:
        return {"user": accounts.current_user(fc_session)}

    @app.put("/api/me/profile")
    def update_profile(req: ProfileUpdate, fc_session: str | None = Cookie(default=None)) -> dict:
        user = need_user(fc_session)
        accounts.save_profile(user["id"], req.profile)
        return {"ok": True}

    @app.get("/api/looks")
    def looks(fc_session: str | None = Cookie(default=None)) -> dict:
        return {"looks": accounts.list_looks(need_user(fc_session)["id"])}

    @app.post("/api/looks")
    def add_look(req: LookRequest, fc_session: str | None = Cookie(default=None)) -> dict:
        user = need_user(fc_session)
        if req.tryon_key and not (config.TRYON_CACHE_DIR / f"{req.tryon_key}.png").exists():
            raise HTTPException(status_code=400, detail="AI 피팅 이미지를 찾을 수 없어요.")
        return {"look": accounts.add_look(user["id"], req.title, req.outfit, req.products, req.tryon_key)}

    @app.delete("/api/looks/{look_id}")
    def delete_look(look_id: int, fc_session: str | None = Cookie(default=None)) -> dict:
        if not accounts.delete_look(need_user(fc_session)["id"], look_id):
            raise HTTPException(status_code=404, detail="저장한 코디를 찾을 수 없어요.")
        return {"ok": True}

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
        # 실제 상품은 화면이 LLM 키워드(item.keyword)로 /api/products를 따로 불러 채움 (구글 쇼핑이 느려서 추천을 막지 않게)
        items = [_item_json(slot, item) for slot, item in slots.items() if item]
        return {
            "weather": format_weather(result["weather_data"]),
            "summary": outfit.summary,
            "weather_tip": outfit.weather_tip,
            "items": items,
            "products_enabled": products_enabled(),
        }

    app.mount("/static", StaticFiles(directory=config.WEB_DIR), name="static")
    app.mount("/avatar-kit", StaticFiles(directory=config.AVATAR_KIT_DIR), name="avatar-kit")
    config.CUTOUT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/cutouts", StaticFiles(directory=config.CUTOUT_CACHE_DIR), name="cutouts")
    config.TRYON_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/tryon", StaticFiles(directory=config.TRYON_CACHE_DIR), name="tryon")  # 저장한 코디의 AI 피팅 이미지

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(config.WEB_DIR / "index.html")

    return app
