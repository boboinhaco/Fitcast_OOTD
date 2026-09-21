"""날씨 조회 Tool (Open-Meteo, API 키 불필요)."""

from datetime import date as date_cls
from typing import Optional

import requests
from langchain_core.tools import tool

from fitcast import config

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# 지오코딩 실패 대비 주요 도시 좌표
CITY_FALLBACK = {
    "서울": (37.5665, 126.9780), "부산": (35.1796, 129.0756),
    "인천": (37.4563, 126.7052), "대구": (35.8714, 128.6014),
    "대전": (36.3504, 127.3845), "광주": (35.1595, 126.8526),
    "울산": (35.5384, 129.3114), "수원": (37.2636, 127.0286),
    "제주": (33.4996, 126.5312), "강릉": (37.7519, 128.8761),
    "전주": (35.8242, 127.1480), "춘천": (37.8813, 127.7298),
}

# WMO 날씨 코드 → 한글 설명
WEATHER_CODES = {
    0: "맑음", 1: "대체로 맑음", 2: "구름 조금", 3: "흐림",
    45: "안개", 48: "짙은 안개",
    51: "약한 이슬비", 53: "이슬비", 55: "강한 이슬비",
    61: "약한 비", 63: "비", 65: "강한 비",
    66: "약한 어는 비", 67: "어는 비",
    71: "약한 눈", 73: "눈", 75: "강한 눈", 77: "싸락눈",
    80: "약한 소나기", 81: "소나기", 82: "강한 소나기",
    85: "약한 눈보라", 86: "눈보라",
    95: "뇌우", 96: "우박 동반 뇌우", 99: "강한 우박 동반 뇌우",
}


def geocode(city: str) -> tuple[float, float, str]:
    """도시 이름을 위도·경도로 변환."""
    try:
        res = requests.get(
            GEOCODE_URL,
            params={"name": city, "count": 1, "language": "ko"},
            timeout=config.HTTP_TIMEOUT,
        )
        res.raise_for_status()
        results = res.json().get("results") or []
        if results:
            top = results[0]
            return top["latitude"], top["longitude"], top.get("name", city)
    except requests.RequestException:
        pass
    # API 실패 시 내장 좌표 사용
    for name, (lat, lon) in CITY_FALLBACK.items():
        if name in city:
            return lat, lon, name
    raise ValueError(f"'{city}'의 위치를 찾지 못했어요. 도시 이름을 다시 확인해 주세요.")


def fetch_weather(city: str, target_date: Optional[str] = None) -> dict:
    """특정 도시·날짜의 날씨를 dict로 반환."""
    lat, lon, resolved = geocode(city)
    day = target_date or date_cls.today().isoformat()
    res = requests.get(
        FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "timezone": "auto",
            "start_date": day,
            "end_date": day,
            "daily": ",".join([
                "weather_code", "temperature_2m_max", "temperature_2m_min",
                "apparent_temperature_max", "apparent_temperature_min",
                "precipitation_probability_max", "precipitation_sum",
                "wind_speed_10m_max", "uv_index_max",
            ]),
        },
        timeout=config.HTTP_TIMEOUT,
    )
    # 예보 범위(약 16일)를 벗어나면 400 응답
    if res.status_code == 400:
        raise ValueError("예보는 오늘부터 약 16일 이내 날짜만 조회할 수 있어요.")
    res.raise_for_status()
    daily = res.json()["daily"]

    def first(key):
        # 하루치 배열의 첫 값 추출
        values = daily.get(key) or [None]
        return values[0]

    t_max, t_min = first("temperature_2m_max"), first("temperature_2m_min")
    return {
        "city": resolved,
        "date": day,
        "condition": WEATHER_CODES.get(first("weather_code"), "알 수 없음"),
        "temp_max": t_max,
        "temp_min": t_min,
        "temp_avg": round((t_max + t_min) / 2, 1) if t_max is not None and t_min is not None else None,
        "feels_max": first("apparent_temperature_max"),
        "feels_min": first("apparent_temperature_min"),
        "rain_prob": first("precipitation_probability_max"),
        "rain_mm": first("precipitation_sum"),
        "wind_kmh": first("wind_speed_10m_max"),
        "uv_index": first("uv_index_max"),
    }


def format_weather(w: dict) -> str:
    """날씨 dict를 LLM이 읽기 좋은 문장으로 변환."""
    return (
        f"[{w['city']} {w['date']}] {w['condition']}, "
        f"최고 {w['temp_max']}°C / 최저 {w['temp_min']}°C "
        f"(체감 {w['feels_max']}°C / {w['feels_min']}°C), "
        f"강수확률 {w['rain_prob']}%, 강수량 {w['rain_mm']}mm, "
        f"최대 풍속 {w['wind_kmh']}km/h, 자외선 지수 {w['uv_index']}"
    )


@tool
def get_weather(city: str, target_date: Optional[str] = None) -> str:
    """도시의 날씨 예보를 조회한다. 옷차림 추천 전에 반드시 먼저 호출한다.

    Args:
        city: 도시 이름 (예: 서울, 제주, 도쿄, Paris)
        target_date: YYYY-MM-DD 형식 날짜. 생략하면 오늘. 오늘부터 약 16일 이내만 가능.
    """
    try:
        return format_weather(fetch_weather(city, target_date))
    except (ValueError, requests.RequestException) as e:
        # 에이전트가 읽고 사용자에게 안내하도록 오류를 문자열로 반환
        return f"날씨 조회 실패: {e}"
