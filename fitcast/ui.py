"""Gradio 화면 구성."""

import os
from datetime import date, timedelta

import gradio as gr

from avatar_kit.avatar_renderer import BODIES, FACES, HAIR, render_avatar
from fitcast import config
from fitcast.agent import chat
from fitcast.chains.outfit import outfit_to_markdown, recommend_outfit
from fitcast.chains.tryon import generate_tryon
from fitcast.chains.vision import analysis_to_markdown, analyze_clothing

# 날짜 선택지 → 오늘 기준 일수
DAY_OFFSETS = {"오늘": 0, "내일": 1, "모레": 2}

PLATFORM_OPTIONS = list(config.SHOP_SEARCH_URLS)

# 아바타 기본 선택값
DEFAULT_FACE, DEFAULT_HAIR, DEFAULT_BODY = "강아지상", "긴 웨이브", "굴곡형"

INTRO = (
    "# 🌤️ Fitcast Lab\n"
    "[← 아바타 피팅룸으로 돌아가기](/)\n\n"
    "일기예보는 봤는데, 뭘 입을지는 모르겠다면. "
    "오늘 날씨와 내 스타일에 딱 맞는 코디를 예보해 드려요."
)


def on_recommend(city, day_label, styles, tpo, gender, platforms, note):
    """'코디 추천받기' 버튼 핸들러."""
    if not city or not city.strip():
        raise gr.Error("도시를 입력해 주세요.")
    target = date.today() + timedelta(days=DAY_OFFSETS.get(day_label, 0))
    try:
        result = recommend_outfit(
            city=city.strip(), styles=styles, tpo=tpo,
            gender=gender, note=note, date=target.isoformat(),
        )
    except ValueError as e:
        # 위치·날짜 오류는 사용자에게 그대로 안내
        raise gr.Error(str(e))
    except Exception as e:
        raise gr.Error(f"추천 중 문제가 생겼어요: {e}")
    # 화면용 마크다운, 원본 결과, 이전 피팅 이미지 초기화
    return outfit_to_markdown(result, platforms or None), result, None


def on_tryon(result, face, hair, body):
    """'AI 피팅 보기' 버튼 핸들러."""
    if not result:
        raise gr.Error("먼저 코디를 추천받아 주세요.")
    try:
        # 아바타 렌더 → 착용 이미지 생성
        avatar = render_avatar(face, hair, body)
        return generate_tryon(avatar, result["outfit"])
    except Exception as e:
        raise gr.Error(f"피팅 이미지 생성 중 문제가 생겼어요: {e}")


def on_analyze(image, platforms):
    """'사진 분석하기' 버튼 핸들러."""
    if image is None:
        raise gr.Error("사진을 먼저 올려 주세요.")
    try:
        result = analyze_clothing(image)
    except Exception as e:
        raise gr.Error(f"분석 중 문제가 생겼어요: {e}")
    return analysis_to_markdown(result, platforms or None)


def build_ui() -> gr.Blocks:
    """탭 3개짜리 Blocks 앱 생성."""
    with gr.Blocks(title="Fitcast") as demo:
        gr.Markdown(INTRO)
        # 키가 없으면 상단에 경고 표시
        if not os.getenv("OPENAI_API_KEY"):
            gr.Markdown("> ⚠️ `OPENAI_API_KEY`가 설정되지 않았어요. `.env` 또는 Spaces Secrets를 확인해 주세요.")

        with gr.Tab("오늘의 코디"):
            with gr.Row():
                with gr.Column(scale=1):
                    city = gr.Textbox(label="도시", value=config.DEFAULT_CITY)
                    day = gr.Radio(list(DAY_OFFSETS), value="오늘", label="날짜")
                    styles = gr.CheckboxGroup(config.STYLE_OPTIONS, label="선호 스타일 (복수 선택)")
                    tpo = gr.Dropdown(config.TPO_OPTIONS, value="일상", label="TPO")
                    gender = gr.Radio(config.GENDER_OPTIONS, value="상관없음", label="성별 핏")
                    platforms = gr.CheckboxGroup(
                        PLATFORM_OPTIONS, value=PLATFORM_OPTIONS[:4], label="검색할 쇼핑 플랫폼",
                    )
                    note = gr.Textbox(label="추가 요청 (선택)", placeholder="예: 치마는 빼줘, 많이 걸을 예정")
                    # 피팅에 쓸 아바타 옵션 (접어두기)
                    with gr.Accordion("내 아바타 설정 (AI 피팅용)", open=False):
                        face = gr.Radio(list(FACES), value=DEFAULT_FACE, label="얼굴 분위기")
                        hair = gr.Radio(list(HAIR), value=DEFAULT_HAIR, label="헤어스타일")
                        body = gr.Radio(list(BODIES), value=DEFAULT_BODY, label="체형")
                    btn = gr.Button("코디 추천받기", variant="primary")
                with gr.Column(scale=2):
                    output = gr.Markdown("왼쪽에서 조건을 고르고 버튼을 눌러 주세요.")
                    # 추천 결과를 피팅 버튼으로 넘기는 보관함
                    outfit_state = gr.State(None)
                    tryon_btn = gr.Button("👗 AI 피팅 보기 (약 1분)")
                    tryon_img = gr.Image(label="착용 이미지", height=700)
            # 추천: 마크다운은 화면에, 원본 결과는 보관함에 저장
            btn.click(
                on_recommend,
                [city, day, styles, tpo, gender, platforms, note],
                [output, outfit_state, tryon_img],
            )
            # 피팅: 보관된 코디 + 아바타 옵션으로 이미지 생성
            tryon_btn.click(on_tryon, [outfit_state, face, hair, body], tryon_img)

        with gr.Tab("챗봇"):
            gr.ChatInterface(
                fn=chat,
                examples=[
                    "이번 주 토요일에 제주도 가는데 뭐 입을까?",
                    "내일 서울 면접인데 비 온대. 어떻게 입지?",
                    "모리걸 스타일인데 30도 넘는 날엔 어떻게 입어?",
                ],
                # 예시 클릭만으로 API가 호출되지 않게 설정
                run_examples_on_click=False,
            )

        with gr.Tab("사진으로 찾기"):
            with gr.Row():
                with gr.Column(scale=1):
                    image = gr.Image(type="pil", label="옷 사진", height=360)
                    platforms_v = gr.CheckboxGroup(
                        PLATFORM_OPTIONS, value=PLATFORM_OPTIONS[:4], label="검색할 쇼핑 플랫폼",
                    )
                    btn_v = gr.Button("사진 분석하기", variant="primary")
                with gr.Column(scale=2):
                    output_v = gr.Markdown("옷 사진을 올리면 비슷한 옷과 매칭 아이템을 찾아 드려요.")
            btn_v.click(on_analyze, [image, platforms_v], output_v)

    return demo