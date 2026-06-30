"""新闻相关路由

包含新闻列表、文章详情、首页与静态资源回退。
所有接口同时支持 GET / POST，POST 用于对接 GamerSky APP 原生请求体格式。
"""

import logging
from typing import Any, Dict, Optional, Tuple

from flask import jsonify, request, send_from_directory

from src.config import config
from src.services.content_service import content_service

logger = logging.getLogger(__name__)

# 支持的栏目标签（白名单）
SUPPORTED_CATEGORIES = {"动态图", "囧图"}


def _error_response(
    message: str, error_code: int = -1, status_code: int = 400
) -> Tuple[Any, int]:
    return (
        jsonify({"success": False, "error": message, "errorCode": error_code}),
        status_code,
    )


def _extract_paging_from_post(data: Dict, default_type: str = "囧图") -> Dict:
    """从 POST 请求体中提取分页参数"""
    request_body = data.get("request") if isinstance(data, dict) else None
    if not isinstance(request_body, dict):
        return {"img_type": default_type, "page_index": 1, "page_size": 20}
    return {
        "img_type": request_body.get("tags", default_type),
        "page_index": request_body.get("pageIndex", 1),
        "page_size": request_body.get("pageSize", 20),
    }


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def register_news_routes(app, cache=None) -> None:
    """注册新闻相关的路由"""
    template_folder = str(app.template_folder) if app.template_folder else "frontend"

    # -----------------------------------------------------------------
    # 健康检查
    # -----------------------------------------------------------------
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({"success": True, "status": "ok", "service": "JT_WEB"})

    # -----------------------------------------------------------------
    # 手动刷新：清空指定范围的缓存
    #   scope = "news_list"        清空某栏目的所有列表缓存
    #   scope = "article_detail"   清空某篇文章的详情缓存
    #   scope = "all"              清空全部缓存（管理员场景）
    # -----------------------------------------------------------------
    @app.route("/api/refresh", methods=["POST"])
    def refresh_cache():
        if not cache:
            return jsonify({"success": True, "cleared": 0, "reason": "cache_disabled"})

        data = request.get_json(silent=True) or {}
        scope = (data.get("scope") or "news_list").lower()
        category = data.get("category")
        article_id = data.get("articleId")

        cleared = 0
        # Flask-Caching 的 SimpleCache 底层字典可通过 cache.cache._cache 访问
        try:
            backend = getattr(cache, "cache", None) or cache
            underlying = getattr(backend, "_cache", None)
            keys = list(underlying.keys()) if hasattr(underlying, "keys") else []
        except Exception:
            keys = []

        if scope == "all":
            cache.clear()
            cleared = -1  # 表示全部
        elif scope == "article_detail" and article_id:
            target = f"article_detail:{article_id}"
            cache.delete(target)
            cleared = 1
        elif scope == "news_list":
            # 清空指定栏目或全部列表缓存
            for key in keys:
                if not key.startswith("news_list:"):
                    continue
                if category and f":{category}:" not in key:
                    continue
                try:
                    cache.delete(key)
                    cleared += 1
                except Exception:
                    pass
        else:
            return _error_response(
                "Invalid refresh scope", error_code=4007, status_code=400
            )

        logger.info(
            "缓存刷新 scope=%s category=%s articleId=%s cleared=%s",
            scope, category, article_id, cleared,
        )
        return jsonify({
            "success": True,
            "scope": scope,
            "category": category,
            "cleared": cleared,
        })

    # -----------------------------------------------------------------
    # 新闻列表
    # -----------------------------------------------------------------
    @app.route("/api/news/list", methods=["GET", "POST"])
    def get_news_list():
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            params = _extract_paging_from_post(data)
        else:
            params = {
                "img_type": request.args.get("type", "囧图"),
                "page_index": request.args.get("page", 1),
                "page_size": request.args.get("size", 20),
            }

        img_type = params["img_type"]
        page_index = _coerce_int(params["page_index"], 1)
        page_size = _coerce_int(params["page_size"], 20)

        if page_index < 1:
            return _error_response(
                "Page index must be greater than 0",
                error_code=4002,
                status_code=400,
            )
        if page_size < 1 or page_size > 100:
            return _error_response(
                "Page size must be between 1 and 100",
                error_code=4003,
                status_code=400,
            )

        cache_key = f"news_list:{img_type}:{page_index}:{page_size}"
        if cache:
            cached_result = cache.get(cache_key)
            if cached_result:
                return jsonify(cached_result)

        result = content_service.get_formatted_news_list(img_type, page_index, page_size)

        if cache and result and result.get("success"):
            cache.set(
                cache_key,
                result,
                timeout=config.get("cache.news_list_timeout", 60),
            )

        if result and result.get("success"):
            return jsonify(result)

        error_message = (
            result.get("error", "Failed to fetch data")
            if isinstance(result, dict)
            else "Failed to fetch data"
        )
        error_code = (
            result.get("errorCode", -1) if isinstance(result, dict) else -1
        )
        # 上游 API 失败时返回 200 + success:false，前端可友好显示错误而非白屏
        return jsonify({"success": False, "error": error_message, "errorCode": error_code}), 200

    # -----------------------------------------------------------------
    # 文章详情
    # -----------------------------------------------------------------
    @app.route("/api/article/detail", methods=["GET", "POST"])
    def get_article_detail():
        article_id: Optional[str] = None
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            request_body = data.get("request") if isinstance(data, dict) else None
            if isinstance(request_body, dict):
                article_id = request_body.get("articleId")
        else:
            article_id = request.args.get("id")

        if not article_id:
            return _error_response(
                "Article ID is required", error_code=4004, status_code=400
            )

        article_id_int = _coerce_int(article_id, 0)
        if article_id_int <= 0:
            return _error_response(
                "Invalid Article ID", error_code=4005, status_code=400
            )

        cache_key = f"article_detail:{article_id_int}"
        if cache:
            cached_result = cache.get(cache_key)
            if cached_result:
                return jsonify(cached_result)

        result = content_service.get_formatted_article_detail(article_id_int)

        if cache and result and result.get("success"):
            cache.set(
                cache_key,
                result,
                timeout=config.get("cache.article_detail_timeout", 300),
            )

        if result and result.get("success"):
            return jsonify(result)

        error_message = (
            result.get("error", "Failed to fetch article")
            if isinstance(result, dict)
            else "Failed to fetch article"
        )
        error_code = (
            result.get("errorCode", -1) if isinstance(result, dict) else -1
        )
        # 上游 API 失败时返回 200 + success:false
        return jsonify({"success": False, "error": error_message, "errorCode": error_code}), 200

    # -----------------------------------------------------------------
    # 首页
    # -----------------------------------------------------------------
    @app.route("/", methods=["GET"])
    def serve_index():
        try:
            return send_from_directory(template_folder, "index.html")
        except Exception as exc:  # noqa: BLE001
            logger.exception("前端页面加载失败: %s", exc)
            return (
                "<h1>错误: 前端页面加载失败</h1>"
                f"<p>{exc}</p>"
            ), 500

    # SPA 深链回退：将 /article/123、/category/动态图 等路由交还前端
    @app.route("/<path:unused>", methods=["GET"])
    def spa_fallback(unused: str):
        # API 路径返回 JSON 404
        if unused.startswith("api/"):
            return (
                jsonify({"success": False, "error": "Not Found", "errorCode": 404}),
                404,
            )
        # 静态资源路径返回纯 404
        if unused.startswith(("static/", "frontend/")):
            return ("Not Found", 404)
        # 其他路径回退到 index.html（SPA 路由）
        try:
            return send_from_directory(template_folder, "index.html")
        except Exception:
            return ("Not Found", 404)
