"""每日囧图 - 应用入口

本地开发：
    python app.py

生产部署（推荐 gunicorn）：
    gunicorn -w 4 -b 0.0.0.0:5000 "src.app_factory:create_app()"

Docker 部署：
    docker compose up -d --build
"""

from src.app_factory import run_app

if __name__ == '__main__':
    run_app()
