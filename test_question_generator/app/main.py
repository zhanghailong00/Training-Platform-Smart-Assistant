"""试题生成助手 — 应用入口"""

import uvicorn
import gradio as gr
from fastapi import FastAPI
from api.routes import router
from ui.gradio_app import create_ui
from core.settings import settings
from core.logger import get_logger

logger = get_logger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="试题生成助手",
    description="基于 DeepSeek 的试题自动生成服务",
    version="1.0.0",
)

# 注册 API 路由
app.include_router(router)

# 挂载 Gradio 界面
ui = create_ui()
gr.mount_gradio_app(app, ui, path="/")

logger.info("试题生成助手启动完成")


def main():
    """直接运行入口"""
    logger.info(f"启动服务: http://{settings.host}:{settings.port}")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
