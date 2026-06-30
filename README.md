# 每日囧图

响应式动态图/囧图专栏浏览网站，Material Design 3 风格。Flask + Vue 3 (CDN)，Docker 一键部署。

## 功能

- 响应式布局，自动/手动深色模式，减少动画偏好支持
- 侧边栏切换"动态图"/"囧图"专栏，Alt+1 / Alt+2 快捷键
- 文章列表 / 详情页，平滑动画，图片懒加载，骨架屏加载占位
- **浏览位置记忆**：列表滚动位置按栏目恢复（详情返回 / 浏览器后退 / 移动端右滑）
- 已读 / 未读标记（localStorage），手动刷新清缓存拉最新数据
- **用户认证**：Session 登录保护，环境变量 / 配置文件启用

## 快速开始

### Docker Hub 镜像（推荐）

```bash
docker pull wdj2613/daily-jiongtu:latest
# 基础启动
docker run -d --name daily-jiongtu -p 5000:5000 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config.json:/app/config.json:ro \
  --restart unless-stopped \
  wdj2613/daily-jiongtu:latest

# 启用认证并设置账号密码
docker run -d --name daily-jiongtu -p 5000:5000 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config.json:/app/config.json:ro \
  -e AUTH_ENABLED=true \
  -e AUTH_USERNAME=myuser \
  -e AUTH_PASSWORD=mypassword \
  -e SECRET_KEY=your-random-secret-key \
  --restart unless-stopped \
  wdj2613/daily-jiongtu:latest
```

> Windows PowerShell 下将 `$(pwd)` 替换为 `${PWD}`。

或使用 docker-compose（无需克隆仓库）：

```yaml
services:
  web:
    image: wdj2613/daily-jiongtu:latest
    ports: ["5000:5000"]
    environment:
      - TZ=Asia/Shanghai
      # 启用认证（可选）
      - AUTH_ENABLED=true
      - AUTH_USERNAME=admin
      - AUTH_PASSWORD=changeme
      - SECRET_KEY=your-random-secret-key
    volumes:
      - ./logs:/app/logs
      - ./config.json:/app/config.json:ro
    restart: unless-stopped
```

```bash
docker compose up -d
```

### 本地构建

```bash
git clone git@github.com:wdj2613/jt_web.git && cd jt_web
docker compose up -d --build
```

### 本地开发

Windows 双击 `start_server.bat`，或手动：

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

访问 `http://localhost:5000`。

**生产环境**（gunicorn）：

```bash
gunicorn -w 4 -b 0.0.0.0:5000 "src.app_factory:create_app()"
```

## 配置

`config.json`（主要配置项）：

```json
{
  "server": { "host": "0.0.0.0", "port": 5000, "debug": false },
  "cache": { "news_list_timeout": 120, "article_detail_timeout": 600 },
  "auth": { "enabled": false, "username": "admin", "password": "changeme", "secret_key": "" },
  "cors": { "origins": "*" }
}
```

**用户认证**：设 `auth.enabled: true` 或环境变量 `AUTH_ENABLED=true`。未登录 → `/login` 页面 / API 返回 401。生产环境务必设固定 `SECRET_KEY`。

环境变量 > config.json：`AUTH_ENABLED` `AUTH_USERNAME` `AUTH_PASSWORD` `SECRET_KEY`。

Docker 中修改 `config.json` 后 `docker compose restart web` 即可，无需重建。

## 数据更新

上游 GamerSky APP API，缓存优先（列表 120s / 详情 600s），过期后下一位访问者触发被动刷新。点击头部刷新按钮 → 清空缓存立即拉取最新数据。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| GET/POST | `/api/news/list` | 新闻列表 |
| GET/POST | `/api/article/detail` | 文章详情 |
| POST | `/api/refresh` | 清空缓存 |

详细文档见 [`docs/API.md`](docs/API.md)。

## 项目结构

```
├── app.py                 # 开发入口
├── config.json            # 配置文件
├── Dockerfile             # 多阶段构建
├── docker-compose.yml
├── frontend/index.html    # Vue 3 单页应用
├── static/                # CSS / JS
├── src/
│   ├── app_factory.py     # Flask 应用工厂
│   ├── config.py
│   ├── datasource/api.py  # GamerSky API 客户端
│   ├── routes/news_routes.py
│   └── services/content_service.py
└── docs/API.md
```

## 架构

三层结构（路由 → 服务 → 数据源），Flask-Caching 内存缓存，bleach 防 XSS，gunicorn 多 worker。前端 Vue 3 CDN + MD3 风格。

## 安全

- Session 认证，bleach HTML 白名单清理（去 script / 内联事件 / 危险协议）
- 图片 `referrerpolicy="no-referrer"`，外链 `rel="noopener noreferrer"`
- CORS 白名单可配，Docker 非 root 运行，生产关闭 debug

## 贡献

欢迎提交 Issue 和 Pull Request。
