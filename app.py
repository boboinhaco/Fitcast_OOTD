"""Fitcast 실행 진입점 (Hugging Face Spaces도 이 파일을 실행)."""

import os

import gradio as gr
import uvicorn

from fitcast.ui import build_ui
from fitcast.web import create_app

# 메인 웹(/)에 기존 Gradio 화면(/lab)을 붙임
demo = build_ui()
app = gr.mount_gradio_app(create_app(), demo, path="/lab", theme=gr.themes.Soft())

if __name__ == "__main__":
    # Spaces는 GRADIO_SERVER_NAME=0.0.0.0을 넣어줌
    uvicorn.run(
        app,
        host=os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"),
        port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
    )
