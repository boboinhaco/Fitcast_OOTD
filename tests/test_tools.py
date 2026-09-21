"""API 키·네트워크 없이 돌아가는 단위 테스트."""

from fitcast.rag.style_guide import load_style_docs, temp_band_guide
from fitcast.tools.shop_links import build_shop_links, make_links
from fitcast.tools.weather import WEATHER_CODES, format_weather


def test_make_links_encodes_keyword():
    # 한글 키워드가 URL 인코딩되는지 확인
    links = make_links("린넨 롱 원피스", ["무신사"])
    assert list(links) == ["무신사"]
    assert "%EB%A6%B0" in links["무신사"]
    assert " " not in links["무신사"]


def test_make_links_ignores_unknown_platform():
    # 등록되지 않은 플랫폼은 무시
    assert make_links("니트", ["없는몰"]) == {}


def test_build_shop_links_tool_returns_markdown():
    # Tool 호출 결과가 마크다운 링크인지 확인
    out = build_shop_links.invoke({"keyword": "와이드 슬랙스"})
    assert "[무신사](" in out and "[지그재그](" in out


def test_temp_band_covers_all_range():
    # -20~45도 전 구간에 가이드가 있는지 확인
    for t in [x / 2 for x in range(-40, 91)]:
        assert "가이드 없음" not in temp_band_guide(t), t


def test_style_docs_split_by_section():
    # 스타일 가이드가 섹션 단위로 분할되는지 확인
    sections = [d.metadata["section"] for d in load_style_docs()]
    assert "모리걸" in sections
    assert "날씨 보정 규칙" in sections


def test_format_weather():
    # 날씨 dict가 문장으로 변환되는지 확인
    text = format_weather({
        "city": "서울", "date": "2026-09-22", "condition": WEATHER_CODES[0],
        "temp_max": 27, "temp_min": 18, "feels_max": 28, "feels_min": 18,
        "rain_prob": 10, "rain_mm": 0, "wind_kmh": 12, "uv_index": 6,
    })
    assert "서울" in text and "27" in text and "맑음" in text
