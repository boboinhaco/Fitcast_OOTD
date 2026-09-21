"""avatar_kit Gradio 데모 (프로젝트 루트에서 python -m avatar_kit.gradio_demo)."""

import gradio as gr

try:
    from .avatar_renderer import BODIES, FACES, HAIR, render_avatar
except ImportError:  # avatar_kit 폴더 안에서 직접 실행할 때
    from avatar_renderer import BODIES, FACES, HAIR, render_avatar


with gr.Blocks(title="Fitcast Avatar Studio") as demo:
    gr.Markdown("# Fitcast Avatar Studio\n얼굴, 헤어스타일, 체형을 골라 가상 피팅 모델을 만들어보세요.")
    with gr.Row():
        with gr.Column(scale=1):
            face = gr.Radio(list(FACES), value="강아지상", label="얼굴 분위기")
            hair = gr.Radio(list(HAIR), value="긴 웨이브", label="헤어스타일")
            body = gr.Radio(list(BODIES), value="굴곡형", label="체형")
        with gr.Column(scale=1):
            preview = gr.Image(
                value=render_avatar("강아지상", "긴 웨이브", "굴곡형"),
                label="나의 아바타",
                height=650,
                format="png",
            )

    for component in (face, hair, body):
        component.change(render_avatar, inputs=[face, hair, body], outputs=preview)


if __name__ == "__main__":
    demo.launch()
