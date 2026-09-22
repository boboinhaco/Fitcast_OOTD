"""회원가입·로그인·저장한 코디 테스트 (임시 SQLite 파일 사용)."""

import pytest
from fastapi.testclient import TestClient

from fitcast import accounts, config
from fitcast.tools import products
from fitcast.web import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "TRYON_CACHE_DIR", tmp_path / "tryon")
    return TestClient(create_app())


def test_signup_login_and_profile(client):
    res = client.post("/api/auth/signup", json={"email": "Me@Test.com", "password": "secret1", "name": "인서", "profile": {"height": 165}})
    assert res.status_code == 200 and res.json()["user"]["email"] == "me@test.com"
    assert client.get("/api/auth/me").json()["user"]["profile"] == {"height": 165}
    # 중복 가입은 400, 틀린 비밀번호는 400
    assert client.post("/api/auth/signup", json={"email": "me@test.com", "password": "secret1", "name": "x"}).status_code == 400
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").json()["user"] is None
    assert client.post("/api/auth/login", json={"email": "me@test.com", "password": "wrong1"}).status_code == 400
    assert client.post("/api/auth/login", json={"email": "me@test.com", "password": "secret1"}).status_code == 200
    client.put("/api/me/profile", json={"profile": {"height": 170, "hair": "bob"}})
    assert client.get("/api/auth/me").json()["user"]["profile"]["hair"] == "bob"


def test_looks_require_login_and_roundtrip(client, tmp_path):
    assert client.get("/api/looks").status_code == 401
    client.post("/api/auth/signup", json={"email": "a@b.co", "password": "secret1", "name": "a"})
    (tmp_path / "tryon").mkdir(exist_ok=True)
    (tmp_path / "tryon" / "abc123.png").write_bytes(b"png")
    bad = client.post("/api/looks", json={"title": "x", "outfit": {}, "tryon_key": "ffff"})
    assert bad.status_code == 400  # 없는 이미지 키
    ok = client.post("/api/looks", json={"title": "가을 코디", "outfit": {"top": {"id": "t01"}}, "products": [{"name": "니트"}], "tryon_key": "abc123"})
    look = ok.json()["look"]
    assert look["tryon_image"] == "/tryon/abc123.png" and look["outfit"]["top"]["id"] == "t01"
    assert [l["title"] for l in client.get("/api/looks").json()["looks"]] == ["가을 코디"]
    assert client.delete(f"/api/looks/{look['id']}").status_code == 200
    assert client.get("/api/looks").json()["looks"] == []


def test_password_hash_is_salted():
    assert accounts._hash("pw", "00" * 16) != accounts._hash("pw", "11" * 16)


def test_excluded_names():
    assert products.is_excluded("폴로 남성 반팔 티셔츠") and products.is_excluded("Nike Men's Tee") and products.is_excluded("오즈키즈 원피스")
    assert not products.is_excluded("여성 케이블 니트") and not products.is_excluded("우먼 데일리 숄더백")
