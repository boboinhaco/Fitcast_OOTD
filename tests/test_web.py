"""웹 API·아바타 모양 코드 테스트 (API 키·네트워크 불필요)."""

import re

from fastapi.testclient import TestClient

from fitcast import config
from fitcast.chains.outfit import shape_guide
from fitcast.web import Profile, create_app, profile_to_text


def test_profile_to_text_includes_body_info():
    # 키·몸무게·체형이 프롬프트 문장에 들어가는지 확인
    text = profile_to_text(Profile(height=160, weight=50, body="삼각형", face="강아지상"))
    assert "160cm" in text and "삼각형" in text and "강아지상" in text and "BMI" in text


def test_shape_guide_lists_every_part():
    # 프롬프트용 모양 코드 목록에 모든 부위가 들어가는지 확인
    guide = shape_guide()
    for part, codes in config.AVATAR_SHAPES.items():
        assert part in guide and codes[0] in guide


def test_avatar_js_draws_every_shape():
    # 백엔드 모양 코드를 프론트 아바타가 전부 그릴 수 있는지 확인
    js = (config.WEB_DIR / "js" / "avatar.js").read_text(encoding="utf-8")
    defined = set(re.findall(r"^\s{4}(\w+)(?:\(S|: \(S)", js, re.M))
    # 안경·벨트는 표 대신 eyewear()·belt() 함수가 따로 그림
    defined |= {"sunglasses", "glasses", "belt"}
    for codes in config.AVATAR_SHAPES.values():
        missing = set(codes) - defined
        assert not missing, missing


def test_config_and_index_served():
    # 메인 페이지와 설정 API가 뜨는지 확인
    client = TestClient(create_app())
    assert client.get("/").status_code == 200
    assert "shop_urls" in client.get("/api/config").json()


def test_recommend_rejects_empty_city():
    # 도시가 비면 LLM 호출 전에 422로 막히는지 확인
    client = TestClient(create_app())
    assert client.post("/api/recommend", json={"city": ""}).status_code == 422


def test_avatar_kit_layout_complete():
    # 빌드된 avatar_kit 레이아웃에 모든 레이어 파일과 골격 좌표가 있는지 확인
    import json

    layout = json.loads((config.AVATAR_KIT_DIR / "layout.json").read_text(encoding="utf-8"))
    assert len(layout["faces"]) == len(layout["hair"]) == len(layout["bodies"]) == 6
    for folder, key in (("faces", "faces"), ("hair", "hair"), ("bodies", "bodies")):
        for name in layout[key]:
            assert (config.AVATAR_KIT_DIR / folder / f"{name}.png").exists(), name
    for name in layout["faces"]:
        assert (config.AVATAR_KIT_DIR / "faces" / f"{name}-hair.png").exists(), name
    needed = {"nw", "sw", "bw", "ww", "hw", "neckY", "shoulderY", "armpitY", "bustY", "waistY", "hipY",
              "crotchY", "kneeY", "ankleY", "rows", "legC", "legW", "armC", "armW", "shoulderLine", "foot"}
    for name, body in layout["bodies"].items():
        assert needed <= set(body["S"]), (name, needed - set(body["S"]))
        S = body["S"]
        # 위→아래 순서가 뒤집히지 않았는지
        assert S["neckY"] < S["armpitY"] < S["waistY"] < S["hipY"] <= S["crotchY"] < S["kneeY"] < S["ankleY"] < 900


def test_avatar_js_kit_ids_exist():
    # avatar.js가 가리키는 체형·헤어 id가 실제 빌드 결과에 있는지 확인
    import json

    layout = json.loads((config.AVATAR_KIT_DIR / "layout.json").read_text(encoding="utf-8"))
    js = (config.WEB_DIR / "js" / "avatar.js").read_text(encoding="utf-8")
    body_ids = re.search(r"const KIT_BODY = \{(.*?)\};", js).group(1)
    hair_ids = re.search(r"const KIT_HAIR = \{(.*?)\};", js).group(1)
    for kit_id in re.findall(r':\s*"([\w-]+)"', body_ids):
        assert kit_id in layout["bodies"], kit_id
    for kit_id in re.findall(r':\s*"([\w-]+)"', hair_ids):
        assert kit_id in layout["hair"], kit_id


def test_kit_served():
    # /avatar-kit 경로로 레이아웃과 이미지가 서빙되는지 확인
    client = TestClient(create_app())
    assert client.get("/avatar-kit/layout.js").status_code == 200
    assert client.get("/avatar-kit/faces/puppy.png").status_code == 200


def test_kit_python_renderer_all_options():
    # Gradio 데모용 PIL 합성이 모든 선택지 조합의 대표값에서 동작하는지 확인
    from avatar_kit.avatar_renderer import BODIES, FACES, HAIR, render_avatar

    for face, hair, body in zip(FACES, list(HAIR)[:6], BODIES):
        img = render_avatar(face, hair, body, height=320)
        assert img.size[1] == 320
    assert render_avatar("강아지상", "번 헤어", "굴곡형", height=320).size[1] == 320
