"""Flask 应用工厂

负责创建并配置 Flask 应用实例：
- 注册路由
- 配置 CORS、缓存
- 初始化日志
- 配置用户认证
"""

import logging
import os
import secrets
import signal
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask
from flask_caching import Cache
from flask_cors import CORS

from .auth import register_auth_routes
from .config import config
from .routes.news_routes import register_news_routes


def _setup_logging(app: Flask) -> None:
    """配置全局日志：控制台 + 滚动文件"""
    log_level = config.get("logging.level", "INFO")
    log_file = config.log_file  # 自动创建目录

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 控制台
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)

    # 文件（防止重复添加）
    if log_file and not any(
        isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == os.path.abspath(log_file)
        for h in root_logger.handlers
    ):
        try:
            file_handler = RotatingFileHandler(
                log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except OSError:
            # 日志目录不可写时仅使用控制台
            pass

    app.logger.setLevel(log_level)


def create_app() -> Flask:
    """应用程序工厂函数"""
    base_dir = Path(__file__).resolve().parent.parent
    static_dir = base_dir / "static"
    template_dir = base_dir / "frontend"

    app = Flask(
        __name__,
        static_folder=str(static_dir),
        template_folder=str(template_dir),
    )

    _setup_logging(app)
    app.logger.info("初始化 JT_WEB 应用...")

    # --- Session 密钥（Flask session 加密用） ---
    # 优先级：环境变量 > config.json > 随机生成
    secret_key = os.environ.get(
        "SECRET_KEY",
        config.get("auth.secret_key", None),
    )
    if not secret_key:
        secret_key = secrets.token_hex(32)
        app.logger.warning(
            "未配置 SECRET_KEY，已生成随机密钥。多进程/重启后所有 session 将失效。"
        )
    app.secret_key = secret_key

    # --- 用户认证（必须在新闻路由之前注册，避免 /login 被 SPA fallback 拦截）---
    register_auth_routes(app)

    # CORS：默认允许同源；如需开放可改为 config 中读取白名单
    cors_origins = config.get("cors.origins", "*")
    if cors_origins == "*":
        CORS(app)
    else:
        CORS(app, origins=cors_origins if isinstance(cors_origins, list) else [cors_origins])

    # 缓存配置
    cache_config = {
        "CACHE_TYPE": config.get("cache.type", "SimpleCache"),
        "CACHE_DEFAULT_TIMEOUT": config.get("cache.default_timeout", 300),
        "CACHE_KEY_PREFIX": config.get("cache.key_prefix", "jt_web_"),
        "CACHE_THRESHOLD": config.get("cache.threshold", 500),
    }
    app.config.from_mapping(cache_config)
    cache = Cache(app)

    # 注册新闻路由
    register_news_routes(app, cache)

    # 日志输出认证状态
    auth_config = config.get("auth.enabled", False) or os.environ.get("AUTH_ENABLED", "").lower() in ("true", "1", "yes")
    app.logger.info("认证状态: %s", "已启用" if auth_config else "未启用")

    # 全局错误处理
    @app.errorhandler(404)
    def handle_404(_err):
        # API 路径返回 JSON，其他返回 index.html 由前端处理
        if request_path_starts_with_api():
            return jsonify({"success": False, "error": "Not Found", "errorCode": 404}), 404
        try:
            return send_index_file(template_dir)
        except Exception:
            return ("Not Found", 404)

    @app.errorhandler(500)
    def handle_500(_err):
        app.logger.exception("服务器内部错误")
        return (
            jsonify({"success": False, "error": "Internal Server Error", "errorCode": 500}),
            500,
        )

    @app.errorhandler(429)
    def handle_429(_err):
        return (
            jsonify({"success": False, "error": "请求过于频繁，请稍后再试", "errorCode": 429}),
            429,
        )

    app.logger.info(
        "JT_WEB 应用初始化完成 - host=%s port=%s debug=%s",
        config.host, config.port, config.debug,
    )
    return app


def request_path_starts_with_api() -> bool:
    """辅助函数：判断当前请求是否为 API 路径"""
    from flask import request
    return request.path.startswith("/api/")


def send_index_file(template_dir: str):
    """辅助函数：发送 index.html"""
    from flask import send_from_directory
    return send_from_directory(template_dir, "index.html")


def run_app() -> None:
    """运行应用程序"""
    app = create_app()

    def signal_handler(sig, frame):  # noqa: ARG001
        print("\n正在优雅地关闭服务器...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"服务器启动配置 - 主机: {config.host}, 端口: {config.port}, 调试模式: {config.debug}")
    print("按 Ctrl+C 优雅关闭服务器")
    print("访问 http://localhost:%s 打开网站" % config.port)

    app.run(host=config.host, port=config.port, debug=config.debug)


if __name__ == "__main__":
    run_app()
