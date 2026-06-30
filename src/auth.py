"""认证鉴权模块

支持通过 config.json 或环境变量配置用户名和密码。
环境变量优先级高于配置文件，适合 Docker 部署时注入凭据。

配置文件 (config.json)：
    "auth": {
        "enabled": false,
        "username": "admin",
        "password": "changeme"
    }

环境变量（覆盖配置文件）：
    AUTH_ENABLED=true
    AUTH_USERNAME=myuser
    AUTH_PASSWORD=mypassword
    SECRET_KEY=<随机密钥>
"""

import os
from functools import wraps
from typing import Optional, Tuple

from flask import (
    jsonify,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)

from .config import config

# ---------------------------------------------------------------------------
# 登录页面 HTML（内联，自包含样式，不依赖前端 SPA）
# ---------------------------------------------------------------------------
_LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>每日囧图 - 登录</title>
<style>
  *,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
  body{
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
    color:#e0e0e0;display:flex;align-items:center;justify-content:center;
    min-height:100vh;padding:16px;
  }
  .card{
    background:#1e2a4a;padding:40px 32px;border-radius:16px;
    box-shadow:0 8px 40px rgba(0,0,0,.45);width:100%;max-width:380px;
    border:1px solid rgba(187,134,252,.15);
  }
  .card h1{text-align:center;margin-bottom:8px;font-size:1.6rem;color:#bb86fc}
  .card .sub{text-align:center;margin-bottom:28px;font-size:.85rem;color:#888}
  .field{margin-bottom:16px}
  .field label{display:block;margin-bottom:6px;font-size:.8rem;color:#aaa;text-transform:uppercase;letter-spacing:.5px}
  .field input{
    width:100%;padding:11px 14px;border:1px solid #2a3a5c;border-radius:10px;
    background:#0d1b36;color:#e0e0e0;font-size:1rem;outline:none;
    transition:border-color .2s,box-shadow .2s;
  }
  .field input:focus{border-color:#bb86fc;box-shadow:0 0 0 3px rgba(187,134,252,.15)}
  .btn{
    width:100%;padding:12px;border:none;border-radius:10px;margin-top:8px;
    background:#bb86fc;color:#1a1a2e;font-size:1rem;font-weight:700;
    cursor:pointer;transition:background .2s,transform .1s;
  }
  .btn:hover{background:#cba0ff}
  .btn:active{transform:scale(.98)}
  .error{
    background:rgba(207,102,121,.15);color:#cf6679;text-align:center;
    padding:10px;border-radius:8px;margin-bottom:16px;font-size:.85rem;
    border:1px solid rgba(207,102,121,.25);
  }
  .hint{text-align:center;margin-top:20px;font-size:.75rem;color:#555}
</style>
</head>
<body>
<div class="card">
  <h1>每日囧图</h1>
  <p class="sub">请输入凭据以继续访问</p>
  {% if error %}<div class="error">{{ error }}</div>{% endif %}
  <form method="post">
    <div class="field">
      <label for="username">用户名</label>
      <input type="text" id="username" name="username" autocomplete="username" required autofocus>
    </div>
    <div class="field">
      <label for="password">密码</label>
      <input type="password" id="password" name="password" autocomplete="current-password" required>
    </div>
    <button class="btn" type="submit">登 录</button>
  </form>
  <p class="hint">凭据由管理员在部署时配置</p>
</div>
</body>
</html>"""

# 无需认证即可访问的路径前缀
_EXEMPT_PREFIXES = ("/login", "/logout", "/api/login", "/api/logout", "/api/health", "/static/")

# ---------------------------------------------------------------------------
# 配置读取
# ---------------------------------------------------------------------------


def get_auth_config() -> dict:
    """获取认证配置，环境变量优先于配置文件"""
    return {
        "enabled": _env_bool("AUTH_ENABLED", config.get("auth.enabled", False)),
        "username": os.environ.get("AUTH_USERNAME", config.get("auth.username", "")),
        "password": os.environ.get("AUTH_PASSWORD", config.get("auth.password", "")),
    }


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name, str(default)).lower()
    return val in ("true", "1", "yes", "on")


# ---------------------------------------------------------------------------
# 装饰器（用于需要单独保护的路由）
# ---------------------------------------------------------------------------


def login_required(f):
    """装饰器：要求登录才能访问。未登录 API 返回 401 JSON，页面请求重定向登录页。"""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth = get_auth_config()
        if not auth["enabled"]:
            return f(*args, **kwargs)
        if session.get("authenticated"):
            return f(*args, **kwargs)
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Unauthorized", "errorCode": 401}), 401
        return redirect(url_for("login_page", next=request.url))

    return decorated


# ---------------------------------------------------------------------------
# before_request 全局拦截
# ---------------------------------------------------------------------------


def _make_before_request_handler():
    """创建 before_request 处理器"""

    def _check_auth() -> Optional[Tuple]:
        auth = get_auth_config()
        if not auth["enabled"]:
            return None

        # 已认证 → 放行
        if session.get("authenticated"):
            return None

        # 白名单路径 → 放行
        path = request.path
        if any(path == p or path.startswith(p + "/") or path.startswith(p) for p in _EXEMPT_PREFIXES):
            return None

        # API 请求 → 401 JSON
        if path.startswith("/api/"):
            return jsonify({"success": False, "error": "Unauthorized", "errorCode": 401}), 401

        # 页面请求 → 重定向登录页
        # 保留原始 URL 以便登录后跳回
        login_url = url_for("login_page")
        if request.url and request.url not in (login_url, request.host_url.rstrip("/") + login_url):
            login_url = url_for("login_page", next=request.url)
        return redirect(login_url)

    return _check_auth


# ---------------------------------------------------------------------------
# 路由注册
# ---------------------------------------------------------------------------


def register_auth_routes(app) -> None:
    """注册认证相关路由和全局拦截器"""

    # --- 登录页面 ---
    @app.route("/login", methods=["GET", "POST"])
    def login_page():
        auth = get_auth_config()
        if not auth["enabled"]:
            return redirect("/")

        # 已登录 → 直接进首页
        if session.get("authenticated"):
            return redirect("/")

        error = None
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if username == auth["username"] and password == auth["password"]:
                session["authenticated"] = True
                session.permanent = True
                next_url = request.args.get("next", "/")
                # 安全：只允许相对路径
                if next_url.startswith("//") or next_url.startswith("http"):
                    next_url = "/"
                return redirect(next_url)
            error = "用户名或密码错误，请重试"

        return render_template_string(_LOGIN_HTML, error=error)

    # --- API 登录 ---
    @app.route("/api/login", methods=["POST"])
    def api_login():
        auth = get_auth_config()
        if not auth["enabled"]:
            return jsonify({"success": True, "message": "Authentication is disabled"})

        data = request.get_json(silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "")

        if username == auth["username"] and password == auth["password"]:
            session["authenticated"] = True
            session.permanent = True
            return jsonify({"success": True, "message": "Login successful"})

        return jsonify({"success": False, "error": "Invalid credentials", "errorCode": 401}), 401

    # --- 登出（页面） ---
    @app.route("/logout")
    def logout_page():
        session.pop("authenticated", None)
        return redirect("/login")

    # --- API 登出 ---
    @app.route("/api/logout", methods=["POST"])
    def api_logout():
        session.pop("authenticated", None)
        return jsonify({"success": True, "message": "Logged out"})

    # --- 全局拦截 ---
    app.before_request(_make_before_request_handler())
