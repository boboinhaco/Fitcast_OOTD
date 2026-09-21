"""상품 사진 누끼·옷장 카탈로그 사진 테스트 (rembg·OpenAI·네트워크 호출은 가짜로 대체)."""

import io
import json
import re

from fastapi.testclient import TestClient
from PIL import Image

from fitcast import config, cutout, tryon
from fitcast.web import create_app


def _rgba(w: int, h: int, color=(40, 40, 40, 255)) -> Image.Image:
    return Image.new("RGBA", (w, h), color)


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def test_garment_score_prefers_flat_garment_over_person():
    # 납작하고 넓은 옷 모양 > 위가 좁고(머리) 살색이 많은 사람 모양
    garment = _rgba(200, 160)
    person = _rgba(80, 260, (0, 0, 0, 0))
    px = person.load()
    for y in range(260):
        half = 12 if y < 40 else 38  # 머리는 좁고 몸은 넓게
        for x in range(40 - half, 40 + half):
            px[x, y] = (225, 175, 145, 255)  # 살색
    assert cutout.garment_score(garment) > cutout.garment_score(person)


def test_product_only_flags_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert cutout.product_only_flags([_png_bytes(_rgba(10, 10))]) is None


def test_tile_sheet_grid_size():
    sheet = Image.open(io.BytesIO(cutout.tile_sheet([_png_bytes(_rgba(30, 50))] * 5)))
    assert sheet.size == (4 * cutout.TILE, 2 * cutout.TILE)


def test_cutout_for_url_uses_cache(tmp_path, monkeypatch):
    # 캐시 파일이 있으면 내려받기·누끼 없이 경로와 크기만 돌려줌
    monkeypatch.setattr(config, "CUTOUT_CACHE_DIR", tmp_path)
    monkeypatch.setattr(cutout, "download", lambda url: (_ for _ in ()).throw(AssertionError("no download")))
    url = "https://encrypted-tbn0.gstatic.com/shopping?q=tbn:abc"
    _rgba(30, 40).save(cutout.cache_path(url))
    out = cutout.cutout_for_url(url)
    assert (out["image"], out["w"], out["h"]) == (f"/cutouts/{cutout.cache_path(url).name}", 30, 40)
    assert out["top"] == 1.0 and out["waist"] == 1.0  # 꽉 찬 사각형이라 기준폭 = 전체 폭


def test_rank_products_puts_product_only_first(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CUTOUT_CACHE_DIR", tmp_path)
    monkeypatch.setattr(cutout, "download", lambda url: _png_bytes(_rgba(20, 30)))
    monkeypatch.setattr(cutout, "remove_background", lambda raw: _rgba(20, 30))
    monkeypatch.setattr(cutout, "product_only_flags", lambda raws: [False, True])
    items = [{"name": "착용컷", "image": "https://a.gstatic.com/1"}, {"name": "상품컷", "image": "https://a.gstatic.com/2"}]
    ranked = cutout.rank_products(items, limit=2)
    assert ranked[0]["name"] == "상품컷" and ranked[0]["cutout"]["w"] == 20
    assert ranked[1]["name"] == "착용컷" and "cutout" not in ranked[1]


def test_api_cutout_rejects_disallowed_url():
    res = TestClient(create_app()).get("/api/cutout", params={"url": "http://evil.example.com/a.jpg"})
    assert res.status_code == 400


def test_local_image_only_inside_catalog_and_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CATALOG_DIR", tmp_path)
    (tmp_path / "t01.png").write_bytes(b"png")
    assert tryon.local_image("/static/catalog/t01.png") == tmp_path / "t01.png"
    assert tryon.local_image("/static/catalog/../secret.png") is None
    assert tryon.local_image("/static/catalog/missing.png") is None
    assert tryon.download_product("/static/catalog/t01.png") == b"png"


def test_catalog_items_have_search_keyword_and_photos_match():
    js = (config.WEB_DIR / "js" / "data.js").read_text(encoding="utf-8")
    ids = re.findall(r'\{ id: "([a-z]\d\d)", tab:', js)
    assert ids and len(re.findall(r'\bq: "', js)) == len(ids)
    photos_js = config.WEB_DIR / "js" / "catalog_photos.js"
    if photos_js.exists():
        photos = json.loads(photos_js.read_text(encoding="utf-8").split("=", 1)[1].strip().rstrip(";"))
        for pid, ph in photos.items():
            assert pid in ids and ph["w"] > 0 and ph["h"] > 0
            assert (config.CATALOG_DIR / ph["image"].rsplit("/", 1)[1]).exists()


def test_avatar_js_places_photo_for_every_slot():
    # 실제 상품 사진을 모든 착용 슬롯에 놓을 수 있는지 (종이인형 방식)
    js = (config.WEB_DIR / "js" / "avatar.js").read_text(encoding="utf-8")
    body = js[js.index("function photoSlot(") : js.index("function drawSlot(")]
    for slot in ("top", "outer", "bottom", "shoes", "bag", "hat", "eyewear", "neck", "belt"):
        assert f'case "{slot}"' in body


def test_kit_layout_has_ponytail_back_layer():
    layout = json.loads((config.AVATAR_KIT_DIR / "layout.json").read_text(encoding="utf-8"))
    assert "ponytail" in layout["hairBack"]
    assert (config.AVATAR_KIT_DIR / "hair" / "ponytail-back.png").exists()


def test_hair_color_pngs_match_data_js():
    # 빌드 스크립트의 컬러 목록이 web/js/data.js HAIR_COLORS와 같고, 컬러별 헤어 PNG가 모두 있는지
    js = (config.WEB_DIR / "js" / "data.js").read_text(encoding="utf-8")
    block = js[js.index("const HAIR_COLORS") : js.index("];", js.index("const HAIR_COLORS"))]
    colors = dict(re.findall(r'id: "(\w+)", ko: "[^"]+", hex: "(#[0-9a-f]{6})"', block))
    build = (config.ROOT_DIR / "avatar_kit" / "tools" / "build_assets.py").read_text(encoding="utf-8")
    line = build[build.index("HAIR_COLORS = {") : build.index("}", build.index("HAIR_COLORS = {"))]
    assert dict(re.findall(r'"(\w+)": "(#[0-9a-f]{6})"', line)) == colors
    layout = json.loads((config.AVATAR_KIT_DIR / "layout.json").read_text(encoding="utf-8"))
    assert layout["hairColors"] == list(colors)
    for cid in colors:
        assert (config.AVATAR_KIT_DIR / "hair" / f"long-straight.{cid}.png").exists()
        assert (config.AVATAR_KIT_DIR / "hair" / f"ponytail-back.{cid}.png").exists()
        assert (config.AVATAR_KIT_DIR / "faces" / f"puppy-hair.{cid}.png").exists()


def test_body_cloth_layers_exist():
    layout = json.loads((config.AVATAR_KIT_DIR / "layout.json").read_text(encoding="utf-8"))
    for body in layout["bodies"]:
        assert (config.AVATAR_KIT_DIR / "bodies" / f"{body}-cloth.png").exists()
