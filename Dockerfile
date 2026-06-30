# ====== 构建阶段 ======
# 使用官方 Python slim 镜像（体积小，约 45MB）
FROM python:3.11-slim AS builder

# 设置环境变量，防止 Python 生成 .pyc 文件并实时刷新日志
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 仅复制依赖文件，利用 Docker 层缓存
COPY requirements.txt .

# 安装依赖到独立目录，便于多阶段复制
RUN pip install --prefix=/install -r requirements.txt

# ====== 运行阶段 ======
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    FLASK_ENV=production

# 安装时区数据并设置时区（解决日志时间不正确的问题）
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata curl \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户运行应用（提升安全性）
RUN groupadd --system app && useradd --system --gid app --home-dir /app --shell /sbin/nologin app

WORKDIR /app

# 从构建阶段复制已安装的 Python 依赖
COPY --from=builder /install /usr/local

# 复制项目文件（.dockerignore 会过滤掉 .venv、__pycache__、logs 等）
COPY --chown=app:app . .

# 复制入口脚本（自动处理缺失/目录化的 config.json）
COPY --chown=app:app docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# 创建日志目录并赋权
RUN mkdir -p logs && chown -R app:app logs

# 赋予 app 用户对 /app 的写权限（gunicorn 需要在此创建 .gunicorn 控制目录）
RUN chown app:app /app

# 切换到非 root 用户
USER app

# 暴露端口
EXPOSE 5000

# 健康检查（每 30 秒一次，超时 5 秒）
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:5000/api/health || exit 1

# 入口脚本：自动创建默认 config.json（如不存在或为目录）
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# 使用 gunicorn 作为生产 WSGI 服务器
# -w 4: 4 个 worker 进程（一般 CPU 核数 * 2 + 1）
# -b 0.0.0.0:5000: 绑定所有网卡
# --timeout 60: worker 超时（秒），应大于 API 请求最大超时时间
# --access-logfile -: 访问日志输出到 stdout
# --error-logfile -: 错误日志输出到 stderr
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "src.app_factory:create_app()"]
