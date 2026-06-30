# 每日囧图

一个流畅浏览动态图与囧图专栏的响应式网站，采用 Material Design 3 风格。
后端 Flask + 前端 Vue 3 (CDN)，支持 Docker Hub 镜像拉取即用，一键部署。

## 功能特性

### 核心功能
- 响应式设计，支持桌面端和移动端自适应布局
- 自动检测系统主题并切换夜间/日间模式，支持手动覆盖
- 侧边栏导航，支持切换"动态图"和"囧图"专栏
- 文章列表和详情页展示，平滑过渡动画
- **浏览位置记忆**：在列表滚动到任意位置进入详情，返回时自动恢复到原位置
- 浏览历史记录（已读/未读标记，使用 localStorage）
- 触摸滑动返回（移动端详情页从左缘右滑）
- URL 状态同步，支持浏览器前进/后退
- 图片懒加载与加载失败占位

### 体验优化
- 骨架屏加载占位
- 错误重试按钮
- **手动刷新按钮**：一键清空后端缓存并拉取上游最新数据
- 返回顶部按钮
- ESC 键关闭侧边栏 / 返回列表
- Alt+1 / Alt+2 快捷切换栏目
- 多张缩略图显示数量徽章
- "已读 / 未读" 状态标记
- 侧边栏打开时锁定背景滚动
- 主题色随系统主题变化
- 减少动画偏好支持 (prefers-reduced-motion)

## 环境要求

| 部署方式 | 要求 |
| --- | --- |
| 本地开发 | Python 3.8+，pip |
| Docker 部署 | Docker 20.10+，Docker Compose v2+ |
| 生产环境 | 任意支持 Docker 的 Linux/macOS/Windows |

## 快速开始

### 方式一：Docker Hub 镜像部署（推荐，无需本地构建）

镜像由 GitHub Actions 自动构建并推送到 Docker Hub，每次 `master` 分支有更新即触发。

```bash
# 拉取最新镜像
docker pull wdj2613/daily-jiongtu:latest

# 启动容器（后台运行，自动重启）
docker run -d \
  --name daily-jiongtu \
  -p 5000:5000 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config.json:/app/config.json:ro \
  --restart unless-stopped \
  wdj2613/daily-jiongtu:latest
```

启动后访问 `http://localhost:5000`。

> **Windows (PowerShell)** 下将 `$(pwd)` 替换为 `${PWD}`。

也可以使用 `docker-compose.yml` 编排。在任意目录创建如下文件：

```yaml
# docker-compose.yml —— 使用预构建镜像，无需克隆仓库
services:
  web:
    image: wdj2613/daily-jiongtu:latest
    container_name: daily-jiongtu
    ports:
      - "5000:5000"
    environment:
      - TZ=Asia/Shanghai
      - PYTHONUNBUFFERED=1
    volumes:
      - ./logs:/app/logs
      - ./config.json:/app/config.json:ro
    restart: unless-stopped
```

然后启动：

```bash
# 确保当前目录下有 config.json（可从仓库复制）
docker compose up -d

# 查看日志
docker compose logs -f

# 更新镜像
docker compose pull && docker compose up -d
```

### 方式二：Docker 本地构建部署

```bash
# 克隆仓库并构建启动
git clone git@github.com:wdj2613/jt_web.git
cd jt_web
docker compose up -d --build

# 查看日志
docker compose logs -f

# 停止
docker compose down
```

启动后访问 `http://localhost:5000`。

**Docker 部署特性**：
- 多阶段构建，最终镜像仅约 120MB
- 使用 gunicorn 作为生产 WSGI 服务器（4 worker）
- 非 root 用户运行，提升安全性
- 内置健康检查（每 30 秒一次）
- 日志持久化到 `./logs/` 目录，容器重启不丢失
- 配置文件 `config.json` 通过只读卷挂载，修改无需重新构建镜像
- 时区设置为 `Asia/Shanghai`

**Docker 开发模式**（支持热重载，端口 5001）：

```bash
docker compose --profile dev up -d --build
```

### 方式三：本地开发

#### Windows

双击运行 `start_server.bat`，或手动执行：

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

启动后访问 `http://localhost:5000`。

### 方式四：生产环境（gunicorn 直接运行）

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
gunicorn -w 4 -b 0.0.0.0:5000 \
  --access-logfile - --error-logfile - \
  "src.app_factory:create_app()"
```

## 配置

服务器配置在 `config.json` 中：

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": false
  },
  "cache": {
    "type": "SimpleCache",
    "default_timeout": 300,
    "key_prefix": "jt_web_",
    "news_list_timeout": 120,
    "article_detail_timeout": 600,
    "threshold": 500
  },
  "api": { "timeout": 30 },
  "cors": { "origins": "*" },
  "logging": {
    "level": "INFO",
    "file": "logs/app.log"
  }
}
```

### 关键配置说明

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `server.debug` | `false` | 调试模式，**生产环境必须为 false** |
| `cache.news_list_timeout` | `120` | 新闻列表缓存秒数 |
| `cache.article_detail_timeout` | `600` | 文章详情缓存秒数 |
| `cors.origins` | `"*"` | CORS 允许来源；限制白名单用数组如 `["https://example.com"]` |
| `logging.file` | `logs/app.log` | 日志文件路径，Docker 中已挂载持久化卷 |

> Docker 部署时，修改 `config.json` 后执行 `docker compose restart web` 即可生效，无需重新构建镜像。

## 使用说明

- 访问 `http://localhost:5000` 打开网站
- 点击左上角菜单按钮打开侧边栏
- 在侧边栏中切换"动态图"和"囧图"专栏
- 点击文章卡片查看详细内容
- 在详情页左上角点击返回列表，或使用浏览器后退，将自动恢复到原浏览位置
- 移动端在详情页可从屏幕左缘右滑返回
- 点击头部"刷新"图标可强制拉取上游最新数据
- 点击右上角太阳/月亮按钮切换白天/夜间模式
- 在侧边栏点击"清空已读记录"可重置已读状态
- 在侧边栏点击"返回首页"会清除该栏目滚动记忆，回到顶部

## 浏览位置记忆说明

本站实现了细粒度的浏览位置记忆：

| 场景 | 行为 |
| --- | --- |
| 在列表中向下滚动 → 进入文章详情 → 点击"返回列表" | 自动恢复到原滚动位置 |
| 在列表中向下滚动 → 进入文章详情 → 按浏览器后退 | 自动恢复到原滚动位置 |
| 在列表中向下滚动 → 进入文章详情 → 移动端左缘右滑返回 | 自动恢复到原滚动位置 |
| 切换到另一个栏目 → 切回原栏目 | 自动恢复该栏目上次的位置与已加载列表 |
| 刷新浏览器（F5） | 通过 sessionStorage 恢复本会话内的位置 |
| 关闭浏览器重开 | sessionStorage 已清空，从顶部开始（已读记录仍在） |
| 点击"返回首页" | 清除该栏目滚动记忆，强制回到顶部 |
| 点击"刷新"按钮 | 清除该栏目滚动记忆，加载新列表后从顶部开始 |

实现方式：内存对象 + `sessionStorage` 持久化，按"栏目"维度保存 `{scrollTop, articles, currentPage, hasMore}`。

## 更新机制说明

本站数据来自上游 GamerSky APP API，**不会主动推送或同步**，而是按需拉取。具体流程：

1. **缓存优先**：用户每次访问列表或详情时，先查后端 `SimpleCache`
   - 命中 → 毫秒级返回（缓存默认 TTL：列表 120 秒，详情 600 秒）
   - 未命中 → 向上游 API 拉取最新数据 → 处理（日期格式化、缩略图拆分、HTML 安全清理）→ 写入缓存 → 返回
2. **自动过期**：缓存到期后，下一位访问者会触发一次"被动刷新"，从而看到上游最新内容
3. **手动刷新**：头部"刷新"按钮 → 调用 `/api/refresh` 清空当前栏目所有缓存 → 立即重新请求第 1 页 → 用户即可看到上游刚发布的新内容
4. **进程重启**：缓存为进程内 SimpleCache，重启 Flask 后会全部清空（下次访问重新拉取）
5. **关闭缓存**：将 `cache.type` 改为 `NullCache` 可禁用缓存（每次都打上游，不推荐）

简而言之：**上游更新后，本站会在缓存 TTL（默认 2 分钟）内自动反映；如需立即看到，点击刷新按钮即可。**

## API 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| POST | `/api/refresh` | 手动清空后端缓存 |
| GET/POST | `/api/news/list` | 获取新闻列表 |
| GET/POST | `/api/article/detail` | 获取文章详情 |
| GET | `/` | 前端主页 |
| GET | `/<path>` | SPA 深链回退到 index.html |

详细 API 文档见 [`docs/API.md`](docs/API.md)。

## 项目结构

```
每日囧图/
├── app.py                    # 主应用入口（开发模式）
├── config.json               # 服务器配置（修改无需重建镜像）
├── requirements.txt          # Python 依赖
├── Dockerfile                # 多阶段构建，生产就绪
├── docker-compose.yml        # 编排文件（含 dev profile）
├── .dockerignore             # Docker 构建过滤
├── .github/workflows/        # GitHub Actions 自动构建
├── .gitignore                # Git 忽略规则
├── start_server.bat          # Windows 一键启动脚本
├── frontend/
│   └── index.html            # 前端单页应用（Vue 3 CDN）
├── static/
│   ├── css/md3-styles.css    # Material Design 3 样式
│   └── js/image-placeholder.js
├── docs/
│   └── API.md                # API 文档
├── logs/                     # 运行日志（Docker 已挂载持久化）
└── src/
    ├── __init__.py
    ├── app_factory.py        # Flask 应用工厂
    ├── config.py             # 配置管理
    ├── datasource/
    │   ├── __init__.py
    │   └── api.py            # GamerSky API 客户端
    ├── routes/
    │   ├── __init__.py
    │   └── news_routes.py    # HTTP 路由
    └── services/
        ├── __init__.py
        └── content_service.py # 业务编排与 HTML 清理
```

## 架构说明

项目采用前后端分离架构：

- **后端**：Flask 框架提供 API 接口
  - 三层结构：路由 → 服务 → 数据源
  - Flask-Caching 提供进程内内存缓存
  - bleach 库进行 HTML 白名单清理（防 XSS）
  - 滚动日志文件，便于排查问题
  - 生产环境通过 gunicorn 运行，多 worker 并发
- **前端**：Vue 3 (CDN) + Tailwind CSS + 原生 CSS 实现 MD3 风格界面
- **数据源**：通过 GamerSky APP API 获取动态图与囧图数据

## 安全说明

- 所有来自上游的 HTML 内容均通过 bleach 进行白名单清理，移除 `<script>`、内联事件、危险协议
- 文章标题/作者等字段通过 `html.escape` 转义
- 图片 URL 强制添加 `referrerpolicy="no-referrer"`
- 外链统一添加 `rel="noopener noreferrer"`
- CORS 可在 config.json 中限制白名单
- Docker 容器以非 root 用户运行
- 生产配置默认关闭 `debug` 模式

## Docker 运维

### 更新镜像

```bash
# Docker Hub 镜像部署（方式一）—— 拉取最新并重建
docker compose pull && docker compose up -d

# 本地构建部署（方式二）—— 重新构建
docker compose up -d --build

# docker run 部署 —— 更新容器
docker pull wdj2613/daily-jiongtu:latest
docker stop daily-jiongtu && docker rm daily-jiongtu
docker run -d --name daily-jiongtu -p 5000:5000 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config.json:/app/config.json:ro \
  --restart unless-stopped \
  wdj2613/daily-jiongtu:latest
```

### 查看日志

```bash
# 实时日志
docker compose logs -f

# 最近 100 行
docker compose logs --tail 100
```

### 重启服务

```bash
# 修改 config.json 后重启
docker compose restart web
```

### 进入容器调试

```bash
docker compose exec web sh
```

### 健康检查

```bash
curl http://localhost:5000/api/health
# {"service":"JT_WEB","status":"ok","success":true}
```

### 查看容器状态

```bash
docker compose ps
```

## 优雅关闭

- 本地开发：控制台按 `Ctrl+C`
- Docker：`docker compose down`（等待请求处理完毕后停止）

## 贡献

欢迎提交 Issue 和 Pull Request 来帮助改进项目。
