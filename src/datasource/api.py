"""GamerSky 数据源层

负责与 GamerSky APP API 通信、原始数据清洗与字段标准化。
所有方法均返回 dict 或 None（网络异常时），上层无需关心 HTTP 细节。
"""

import logging
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GamerSkyAPI:
    """GamerSky APP API 客户端"""

    def __init__(self) -> None:
        self.base_url = "http://appapi2.gamersky.com/v5/"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            ),
        }
        # API 设备指纹信息（与原 APP 行为一致）
        self.api_config = {
            "app": "GSAPP",
            "deviceType": "M2006J10C",
            "appVersion": "5.13.61",
            "os": "android",
            "osVersion": "11",
            "deviceId": "4034c60353b640dbaf408ee71f1d68a2",
        }

    # ------------------------------------------------------------------
    # 新闻列表
    # ------------------------------------------------------------------
    def get_news_list(
        self, img_type: str, page_index: int = 1, page_size: int = 20
    ) -> Optional[Dict[str, Any]]:
        """获取新闻列表

        :param img_type: 栏目标签（动态图 / 囧图）
        :param page_index: 页码（从 1 开始）
        :param page_size: 每页条数
        :return: 处理后的 dict，网络异常时返回 None
        """
        url = f"{self.base_url}getCMSNewsList"
        payload = {
            **self.api_config,
            "request": {
                "modelFieldNames": "Title,Author,ThumbnailsPicUrl,updateTime,mark,contentId",
                "tagIds": "",
                "pageSize": page_size,
                "cacheMinutes": 1,
                "tags": img_type,
                "recommendedIndex": 0,
                "nodeIds": "",
                "systemFieldNames": "DefaultPicUrl",
                "pageIndex": page_index,
                "UpdateTime": 0,
                "topicIds": "",
                "GameLib": "0",
                "order": "timeDesc",
            },
        }

        try:
            response = requests.post(
                url, headers=self.headers, json=payload, timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return self.process_news_list(data)
        except requests.exceptions.Timeout:
            logger.warning("请求新闻列表超时: %s (type=%s, page=%s)", url, img_type, page_index)
            return None
        except requests.exceptions.RequestException as exc:
            logger.error("请求新闻列表失败: %s (type=%s, page=%s)", exc, img_type, page_index)
            return None
        except ValueError as exc:
            logger.error("解析新闻列表 JSON 失败: %s", exc)
            return None

    def process_news_list(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗新闻列表数据，统一字段名"""
        if not raw_data or raw_data.get("errorCode") != 0:
            return raw_data

        processed_result: List[Dict[str, Any]] = []
        for article in raw_data.get("result", []):
            thumbnails = self._parse_thumbnails(article.get("ThumbnailsPicUrl"))
            processed_article = {
                "id": article.get("contentId") or article.get("id"),
                "title": article.get("Title", ""),
                "author": article.get("Author", "未知"),
                "updateTime": self.format_date(article.get("updateTime", "")),
                "thumbnail": thumbnails[0] if thumbnails else None,
                "thumbnails": thumbnails,
                "contentId": article.get("contentId", article.get("id")),
            }
            processed_result.append(processed_article)

        return {
            "errorCode": raw_data.get("errorCode", 0),
            "errorMessage": raw_data.get("errorMessage", ""),
            "result": processed_result,
            "total": len(processed_result),
        }

    # ------------------------------------------------------------------
    # 文章详情
    # ------------------------------------------------------------------
    def get_article_detail(self, article_id: int) -> Optional[Dict[str, Any]]:
        """获取文章详情"""
        url = f"{self.base_url}getArticle"
        payload = {
            **self.api_config,
            "request": {
                "extraFiledNames": "",
                "modelFieldNames": (
                    "Tag,Tag_Index,pageNames,Title,Subheading,Author,pcPageURL,"
                    "CopyFrom,UpdateTime,DefaultPicUrl,GameScore,GameLib,TitleIntact,"
                    "NodeId,editor,AudioUrl,AudioDuration,Content_Index"
                ),
                "articleId": article_id,
                "appModelFieldNames": "",
                "cacheMinutes": 10,
            },
        }

        try:
            response = requests.post(
                url, headers=self.headers, json=payload, timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return self.process_article_detail(data)
        except requests.exceptions.Timeout:
            logger.warning("请求文章详情超时: %s (articleId=%s)", url, article_id)
            return None
        except requests.exceptions.RequestException as exc:
            logger.error("请求文章详情失败: %s (articleId=%s)", exc, article_id)
            return None
        except ValueError as exc:
            logger.error("解析文章详情 JSON 失败: %s", exc)
            return None

    def process_article_detail(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗文章详情数据"""
        if not raw_data or raw_data.get("errorCode") != 0 or not raw_data.get("result"):
            return raw_data

        article = raw_data["result"][0]
        processed_article = {
            "id": article.get("contentId", article.get("id")),
            "title": article.get("Title", ""),
            "subtitle": article.get("Subheading", ""),
            "author": article.get("Author", "未知"),
            "updateTime": self.format_date(article.get("UpdateTime", "")),
            "copyFrom": article.get("CopyFrom", "网络整理"),
            "content": self.parse_content_pages(article.get("Content_Index", "")),
            "defaultPicUrl": article.get("DefaultPicUrl"),
        }

        return {
            "errorCode": raw_data.get("errorCode", 0),
            "errorMessage": raw_data.get("errorMessage", ""),
            "result": [processed_article],
        }

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    def parse_content_pages(self, content_index: str) -> List[str]:
        """将 Content_Index 按 [NextPage] 分割成页面数组"""
        if not content_index:
            return [""]
        pages = content_index.split("[NextPage]")
        cleaned_pages = [page.strip() for page in pages if page and page.strip()]
        return cleaned_pages if cleaned_pages else [""]

    @staticmethod
    def _parse_thumbnails(value: Any) -> List[str]:
        """ThumbnailsPicUrl 可能是单个 URL、逗号分隔字符串、或已是列表

        :returns: 去重后的 URL 列表（最多保留 9 个）
        """
        if not value:
            return []
        if isinstance(value, list):
            urls = [str(v).strip() for v in value if v and str(v).strip()]
        elif isinstance(value, str):
            urls = [u.strip() for u in value.split(",") if u.strip()]
        else:
            urls = [str(value).strip()]

        # 去重并保留顺序
        seen = set()
        unique: List[str] = []
        for url in urls:
            if url and url not in seen:
                seen.add(url)
                unique.append(url)
        return unique[:9]

    @staticmethod
    def format_date(date_string: str) -> str:
        """格式化日期字符串为 YYYY-MM-DD

        兼容 GamerSky 多种返回格式：
        - "2024-01-15T10:30:00Z"
        - "2024-01-15 10:30:00"
        - "2024-01-15"
        - "/Date(1705305600000+0800)/"
        """
        if not date_string:
            return ""
        text = str(date_string).strip()
        if not text:
            return ""

        # /Date(1705305600000+0800)/  —— 仅取时间戳部分，忽略时区偏移
        if text.startswith("/Date(") and text.endswith(")/"):
            inner = text[len("/Date("):-len(")/")]
            # 截断到 + 或 - 之前（即时间戳部分）
            ts_str = inner.split("+", 1)[0].split("-", 1)[0]
            if ts_str.isdigit():
                try:
                    return datetime.fromtimestamp(int(ts_str) / 1000).strftime("%Y-%m-%d")
                except (ValueError, OSError):
                    return text

        # 优先尝试 ISO 解析
        iso_text = text.replace("Z", "+00:00").replace(" ", "T")
        try:
            return datetime.fromisoformat(iso_text).strftime("%Y-%m-%d")
        except ValueError:
            pass

        # 兜底：尝试常见格式
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return text


# 全局单例
api_instance = GamerSkyAPI()
