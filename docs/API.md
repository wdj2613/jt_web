# API Documentation

## Base URL

- Local: `http://localhost:5000`

## Response Format

### Success

```json
{
  "success": true,
  "data": {}
}
```

### Error

```json
{
  "success": false,
  "error": "Error message",
  "errorCode": 4001
}
```

## Endpoints

### `/api/health`

健康检查，仅支持 `GET`。

```json
{ "success": true, "status": "ok", "service": "JT_WEB" }
```

### `/api/news/list`

获取新闻列表，支持 `GET` 和 `POST`。

#### GET Query Parameters

- `type`: 图片类型，默认 `囧图`（可选值：`动态图` / `囧图`）
- `page`: 页码，默认 `1`
- `size`: 每页数量，默认 `20`，范围 `1-100`

#### POST Body

```json
{
  "request": {
    "tags": "动态图",
    "pageIndex": 1,
    "pageSize": 20
  }
}
```

#### Success Response

```json
{
  "success": true,
  "data": [
    {
      "id": 2076889,
      "title": "示例标题",
      "author": "未知",
      "updateTime": "2026-01-16",
      "thumbnail": "https://example.com/a.jpg",
      "thumbnails": [],
      "contentId": 2076889
    }
  ],
  "total": 20,
  "page_info": {
    "current_page": 1,
    "page_size": 20,
    "has_more": true
  }
}
```

#### Validation Error Codes

- `4001`: 页码/分页参数格式错误
- `4002`: 页码必须大于 0
- `4003`: 每页数量必须在 1-100 之间

### `/api/article/detail`

获取文章详情，支持 `GET` 和 `POST`。

#### GET Query Parameters

- `id`: 文章 ID，必须为正整数

#### POST Body

```json
{
  "request": {
    "articleId": 2076889
  }
}
```

#### Success Response

```json
{
  "success": true,
  "data": {
    "id": 2076889,
    "title": "示例标题",
    "subtitle": "示例副标题",
    "author": "未知",
    "updateTime": "2026-01-16",
    "copyFrom": "网络整理",
    "content_html": "<p>正文内容</p>",
    "content_pages": [
      "<p>正文内容</p>"
    ],
    "defaultPicUrl": "https://example.com/default.jpg"
  }
}
```

#### Validation Error Codes

- `4004`: 缺少文章 ID
- `4005`: 文章 ID 格式错误
- `4006`: 文章 ID 必须大于 0

### `/api/refresh`

手动清空后端缓存，强制下次请求向 GamerSky 上游 API 拉取最新数据。
仅支持 `POST`，请求体格式：

```json
{
  "scope": "news_list",
  "category": "囧图"
}
```

#### 参数说明

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `scope` | 是 | 刷新范围：`news_list` / `article_detail` / `all` |
| `category` | 否 | 当 `scope=news_list` 时指定栏目（如 `囧图` / `动态图`）；不传则清空所有栏目 |
| `articleId` | 否 | 当 `scope=article_detail` 时指定文章 ID |

#### 成功响应

```json
{
  "success": true,
  "scope": "news_list",
  "category": "囧图",
  "cleared": 3
}
```

`cleared` 表示被清除的缓存条数；若 `scope=all`，则 `cleared=-1`。

#### 错误码

- `4007`: 无效的 `scope` 值

## 缓存与更新机制

### 服务端缓存

| 缓存对象 | 缓存键 | 默认 TTL | 配置项 |
| --- | --- | --- | --- |
| 新闻列表 | `news_list:{栏目}:{页码}:{每页数量}` | 120 秒 | `cache.news_list_timeout` |
| 文章详情 | `article_detail:{文章ID}` | 600 秒 | `cache.article_detail_timeout` |

缓存采用进程内 `SimpleCache`，重启 Flask 进程后会清空。

### 上游数据更新流程

1. GamerSky APP 上游（`appapi2.gamersky.com`）每日新增内容
2. 本站用户访问列表或详情时：
   - 若对应缓存键存在且未过期 → 直接返回缓存（毫秒级响应）
   - 若缓存过期或不存在 → 向上游 API 拉取最新数据，处理后写入缓存并返回
3. 因此新内容最迟在缓存 TTL（默认 120 秒）后会被首次访问的用户拉取到

### 手动强制刷新

- 前端点击头部"刷新"按钮 → 调用 `/api/refresh` 清空当前栏目缓存 → 重新请求第 1 页
- 适合在已知上游已更新但缓存未过期时使用

### 关闭缓存

将 `config.json` 中 `cache.type` 改为 `NullCache` 可禁用所有缓存，每次请求都直接打到上游 API（不推荐，会显著增加响应时间）。
