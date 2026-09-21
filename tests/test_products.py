"""실제 상품 검색·AI 피팅 테스트 (네이버·OpenAI 호출은 가짜 응답으로 대체)."""

import base64
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from fitcast import config
from fitcast import tryon
from fitcast.tools import products
from fitcast.web import create_app


def _png_data_url() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (8, 16), "white").save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


@pytest.fixture
def no_keys(monkeypatch):
    monkeypatch.setattr(config, "SERPAPI_KEY", "")
    monkeypatch.setattr(config, "NAVER_CLIENT_ID", "")
    monkeypatch.setattr(config, "NAVER_CLIENT_SECRET", "")
    products._search.cache_clear()


@pytest.fixture
def fake_naver(monkeypatch):
    monkeypatch.setattr(config, "SERPAPI_KEY", "")
    monkeypatch.setattr(config, "NAVER_CLIENT_ID", "id")
    monkeypatch.setattr(config, "NAVER_CLIENT_SECRET", "secret")
    products._search.cache_clear()
    payload = {"items": [
        {"title": "원목 <b>의자</b>", "image": "https://shopping-phinf.pstatic.net/a.jpg", "category1": "가구/인테리어", "lprice": "9000"},
        {"title": "<b>린넨</b> 롱 스커트 &amp; 벨트", "image": "https://shopping-phinf.pstatic.net/b.jpg", "category1": "패션의류",
         "brand": "", "maker": "", "mallName": "무신사", "lprice": "39000", "link": "https://example.com/p"},
    ]}
    calls = []
    monkeypatch.setattr(products.requests, "get", lambda *a, **k: calls.append(k) or FakeResponse(payload))
    return calls


def test_clean_title_strips_tags_and_entities():
    assert products.clean_title("<b>린넨</b> 셔츠 &amp; 팬츠") == "린넨 셔츠 & 팬츠"


def test_fetch_products_requires_keys(no_keys):
    with pytest.raises(products.ProductSearchError):
        products.fetch_products("린넨 스커트")


def test_fetch_products_prefers_fashion(fake_naver):
    items = products.fetch_products("린넨 스커트", 5)
    assert [i["name"] for i in items] == ["린넨 롱 스커트 & 벨트"]
    assert items[0]["brand"] == "무신사" and items[0]["price"] == 39000
    assert fake_naver[0]["headers"]["X-Naver-Client-Id"] == "id"


@pytest.fixture
def fake_serpapi(monkeypatch):
    monkeypatch.setattr(config, "SERPAPI_KEY", "key")
    products._search.cache_clear()
    calls = []

    def fake_get(url, params=None, **kw):
        calls.append(params["q"])
        # 긴 키워드는 결과 없음 → 짧은 키워드로 재시도하는지 확인
        if len(params["q"].split()) >= 3:
            return FakeResponse({"error": "Google hasn't returned any results for this query."})
        return FakeResponse({"shopping_results": [
            {"title": "니트 볼레로 [IVORY]", "source": "원더플레이스", "extracted_price": 29500,
             "thumbnail": "https://encrypted-tbn0.gstatic.com/shopping?q=tbn:abc", "product_link": "https://www.google.com/p/1"},
            {"title": "이미지 없는 상품", "source": "x", "extracted_price": 1},
        ]})

    monkeypatch.setattr(products.requests, "get", fake_get)
    return calls


def test_serpapi_retries_shorter_keyword(fake_serpapi):
    items = products.fetch_products("아이보리 니트 볼레로", 5)
    assert fake_serpapi == ["아이보리 니트 볼레로", "니트 볼레로"]
    assert items == [{"name": "니트 볼레로 [IVORY]", "brand": "원더플레이스", "mall": "원더플레이스", "price": 29500,
                      "image": "https://encrypted-tbn0.gstatic.com/shopping?q=tbn:abc", "link": "https://www.google.com/p/1"}]


def test_serpapi_preferred_over_naver(fake_serpapi, monkeypatch):
    monkeypatch.setattr(config, "NAVER_CLIENT_ID", "id")
    monkeypatch.setattr(config, "NAVER_CLIENT_SECRET", "secret")
    assert products.provider() == "serpapi"


def test_search_products_tool_without_keys(no_keys):
    out = products.search_products.invoke({"keyword": "니트"})
    assert "build_shop_links" in out


def test_api_products_without_keys(no_keys):
    data = TestClient(create_app()).get("/api/products", params={"q": "니트"}).json()
    assert data == {"enabled": False, "items": [], "error": data["error"]} and data["error"]


def test_allowed_image_url():
    assert tryon.allowed_image_url("https://shopping-phinf.pstatic.net/main_1/a.jpg")
    assert tryon.allowed_image_url("https://encrypted-tbn0.gstatic.com/shopping?q=tbn:abc")
    assert not tryon.allowed_image_url("http://shopping-phinf.pstatic.net/a.jpg")
    assert not tryon.allowed_image_url("https://evil.example.com/pstatic.net.jpg")
    assert not tryon.allowed_image_url("https://127.0.0.1/a.jpg")


def test_tryon_needs_products():
    with pytest.raises(tryon.TryOnError):
        tryon.generate_tryon(_png_data_url(), [])


def test_tryon_returns_cached_result(tmp_path, monkeypatch):
    # 같은 입력으로 저장된 결과가 있으면 API 없이 바로 돌려줌 (시연용)
    monkeypatch.setattr(config, "TRYON_CACHE_DIR", tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    avatar = _png_data_url()
    items = [{"image": "https://shopping-phinf.pstatic.net/b.jpg", "name": "린넨 스커트", "label": "하의"}]
    key = tryon.cache_key(tryon.fit_canvas(tryon.to_png(tryon.decode_data_url(avatar), max_side=1536)), items)
    (tmp_path / f"{key}.png").write_bytes(b"fake-png")
    out = tryon.generate_tryon(avatar, items)
    assert out["cached"] and out["image"].endswith(base64.b64encode(b"fake-png").decode())


def test_tryon_api_errors_are_400(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TRYON_CACHE_DIR", tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(create_app())
    body = {"avatar": _png_data_url(), "products": [{"image": "https://shopping-phinf.pstatic.net/b.jpg"}]}
    res = client.post("/api/tryon", json=body)
    assert res.status_code == 400 and "OPENAI_API_KEY" in res.json()["detail"]


def test_relevance_prefers_item_noun():
    names = ["몸매 보정 버튼 니트", "크롭 니트 볼레로 아이보리", "볼레로 가디건"]
    ranked = sorted(names, key=lambda n: -products.relevance("아이보리 니트 볼레로", n))
    assert ranked[0] == "크롭 니트 볼레로 아이보리" and ranked[-1] == "몸매 보정 버튼 니트"
