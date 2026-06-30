"""内容服务层

负责业务编排与 HTML 渲染。对原始 API 数据做最终加工，
输出前端可直接消费的结构化数据。
"""

import html
import logging
import re
from typing import Dict, List, Optional

try:
    import bleach
    _HAS_BLEACH = True
except ImportError:  # bleach 未安装时回退到正则清理
    bleach = None
    _HAS_BLEACH = False

from ..datasource.api import api_instance

logger = logging.getLogger(__name__)

# 允许的 HTML 标签白名单
_ALLOWED_TAGS = [
    "a", "abbr", "b", "blockquote", "br", "caption", "cite", "code",
    "dd", "del", "div", "dl", "dt", "em", "figcaption", "figure",
    "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "ins",
    "kbd", "li", "mark", "ol", "p", "pre", "q", "s", "samp", "small",
    "span", "strong", "sub", "sup", "table", "tbody", "td", "tfoot",
    "th", "thead", "tr", "u", "ul", "video", "source", "iframe",
]

# 允许的 HTML 属性白名单
_ALLOWED_ATTRS = {
    "*": ["class"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height", "referrerpolicy", "loading"],
    "iframe": ["src", "width", "height", "frameborder", "allowfullscreen"],
    "video": ["src", "controls", "width", "height", "poster"],
    "source": ["src", "type"],
}

# 允许的 URL 协议
_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


class ContentService:
    """内容服务层"""

    def __init__(self) -> None:
        self.api = api_instance

    # ------------------------------------------------------------------
    # 新闻列表
    # ------------------------------------------------------------------
    def get_formatted_news_list(
        self, img_type: str, page_index: int = 1, page_size: int = 20
    ) -> Dict:
        """获取格式化的新闻列表"""
        raw_data = self.api.get_news_list(img_type, page_index, page_size)
        if not raw_data or not isinstance(raw_data, dict):
            logger.warning("获取新闻列表失败: 上游返回为空 (type=%s)", img_type)
            return {"success": False, "error": "无法获取新闻列表", "errorCode": -1}

        if raw_data.get("errorCode") != 0:
            return {
                "success": False,
                "error": raw_data.get("errorMessage", "获取新闻列表失败"),
                "errorCode": raw_data.get("errorCode", -1),
            }

        articles = raw_data.get("result", [])
        formatted_articles: List[Dict] = []
        for article in articles:
            formatted_article = {
                "id": article.get("contentId", article.get("id")),
                "title": html.escape(article.get("Title", article.get("title", ""))),
                "author": html.escape(article.get("Author", article.get("author", "未知"))),
                "updateTime": article.get("updateTime", article.get("UpdateTime", "")),
                "thumbnail": article.get("ThumbnailsPicUrl", article.get("thumbnail")),
                "thumbnails": article.get("thumbnails", []),
                "contentId": article.get("contentId", article.get("id")),
            }
            formatted_articles.append(formatted_article)

        return {
            "success": True,
            "data": formatted_articles,
            "total": raw_data.get("total", len(formatted_articles)),
            "page_info": {
                "current_page": page_index,
                "page_size": page_size,
                # 简单判断是否还有更多数据
                "has_more": len(formatted_articles) == page_size,
            },
        }

    # ------------------------------------------------------------------
    # 文章详情
    # ------------------------------------------------------------------
    def get_formatted_article_detail(self, article_id: int) -> Dict:
        """获取格式化的文章详情"""
        raw_data = self.api.get_article_detail(article_id)
        if not raw_data or not isinstance(raw_data, dict):
            logger.warning("获取文章详情失败: 上游返回为空 (articleId=%s)", article_id)
            return {"success": False, "error": "无法获取文章数据", "errorCode": -1}

        if raw_data.get("errorCode") != 0:
            return {
                "success": False,
                "error": raw_data.get("errorMessage", "获取文章详情失败"),
                "errorCode": raw_data.get("errorCode"),
            }

        if not raw_data.get("result"):
            return {"success": False, "error": "文章不存在或数据为空"}

        article = raw_data["result"][0]
        content_pages: Optional[List[str]] = article.get("content")
        if content_pages is None:
            content_pages = article.get("Content_Index", [""])
        if isinstance(content_pages, str):
            content_pages = [content_pages]

        content_html = self._render_content_pages(content_pages)

        formatted_article = {
            "id": article.get("id"),
            "title": html.escape(article.get("Title", article.get("title", ""))),
            "subtitle": html.escape(article.get("Subheading", article.get("subtitle", ""))),
            "author": html.escape(article.get("Author", article.get("author", "未知"))),
            "updateTime": article.get("UpdateTime", article.get("updateTime", "")),
            "copyFrom": html.escape(article.get("CopyFrom", article.get("copyFrom", "网络整理"))),
            "content_html": content_html,
            "content_pages": content_pages,
            "defaultPicUrl": article.get("DefaultPicUrl"),
        }

        return {"success": True, "data": formatted_article}

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _render_content_pages(self, content_pages: List[str]) -> str:
        """将内容页面数组渲染为 HTML 字符串"""
        if not content_pages:
            return "<p>暂无内容</p>"
        safe_pages = [
            self._sanitize_html(page)
            for page in content_pages
            if page and page.strip()
        ]
        return "".join(safe_pages) if safe_pages else "<p>暂无内容</p>"

    def _sanitize_html(self, html_content: str) -> str:
        """HTML 清理，移除危险脚本与事件处理器

        优先使用 bleach（若已安装）；否则回退到正则清理。
        """
        if not html_content:
            return ""

        if _HAS_BLEACH:
            try:
                cleaned = bleach.clean(
                    html_content,
                    tags=_ALLOWED_TAGS,
                    attributes=_ALLOWED_ATTRS,
                    protocols=_ALLOWED_PROTOCOLS,
                    strip=True,
                    strip_comments=True,
                )
                # 给所有 <a> 添加安全属性
                cleaned = re.sub(
                    r"<a\b(?![^>]*\brel=)([^>]*)>",
                    r'<a\1 rel="noopener noreferrer" target="_blank">',
                    cleaned,
                    flags=re.IGNORECASE,
                )
                # 给所有 <img> 添加 referrerpolicy
                cleaned = re.sub(
                    r"<img\b(?![^>]*\breferrerpolicy=)([^>]*)>",
                    r'<img\1 referrerpolicy="no-referrer" loading="lazy">',
                    cleaned,
                    flags=re.IGNORECASE,
                )
                return cleaned
            except Exception as exc:  # noqa: BLE001 - bleach 异常时回退
                logger.warning("bleach 清理失败，回退到正则清理: %s", exc)

        # 正则回退方案
        clean_content = re.sub(
            r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
            "",
            html_content,
            flags=re.IGNORECASE,
        )
        clean_content = re.sub(
            r"<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>",
            "",
            clean_content,
            flags=re.IGNORECASE,
        )
        clean_content = re.sub(
            r"\s*on\w+\s*=\s*[\"'][^\"']*[\"']",
            "",
            clean_content,
            flags=re.IGNORECASE,
        )
        clean_content = re.sub(
            r"(?i)(javascript:|vbscript:|data:text/html)",
            "",
            clean_content,
        )
        return clean_content


content_service = ContentService()
