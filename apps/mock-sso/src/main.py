from __future__ import annotations

from html import escape
from typing import Annotated
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from src.config import demo_redirect, settings
from src.store import (
    SEED_USERS,
    consume_code,
    create_code,
    create_token,
    resolve_token,
)

app = FastAPI(title="Club League Mock SSO", version="0.1.0")

_PAGE_CSS = """
:root { color-scheme: light dark; font-family: system-ui, sans-serif; }
body { margin: 0; min-height: 100vh; display: grid; place-items: center;
       background: #0f1419; color: #e7ecf1; }
.card { width: min(440px, 92vw); background: #1a2330; border: 1px solid #2c3a4d;
        border-radius: 12px; padding: 1.5rem 1.75rem; }
h1 { margin: 0 0 .75rem; font-size: 1.3rem; }
p { margin: 0 0 .75rem; }
.hint { color: #93a4b8; font-size: .9rem; }
label { display: block; margin-bottom: .75rem; }
select, button { font: inherit; border-radius: 8px; }
select { width: 100%; padding: .5rem; margin-top: .25rem; background: #0f1419;
         color: #e7ecf1; border: 1px solid #2c3a4d; }
button, .btn { appearance: none; border: 0; padding: .65rem 1rem; font-weight: 600;
               cursor: pointer; background: #3b82f6; color: #fff; text-decoration: none;
               display: inline-block; }
button:hover, .btn:hover { background: #2563eb; }
.error { color: #fca5a5; }
dl { display: grid; gap: .5rem; margin: 0 0 1rem; }
dl div { display: grid; grid-template-columns: 110px 1fr; gap: .5rem; }
dt { color: #93a4b8; margin: 0; } dd { margin: 0; word-break: break-all; }
a { color: #93c5fd; }
"""


def _page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>{_PAGE_CSS}</style>
</head>
<body>
  <div class="card">
    {body}
  </div>
</body>
</html>
"""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class UserinfoResponse(BaseModel):
    sub: str
    email: str
    name: str


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    authorize_qs = urlencode(
        {
            "client_id": settings.client_id,
            "redirect_uri": demo_redirect(),
            "response_type": "code",
            "state": "demo",
        }
    )
    body = f"""
    <h1>Club League Mock SSO</h1>
    <p class="hint">Dev-only OAuth2 provider + demo client. Roles/sudo live in the API DB only.</p>
    <p><a class="btn" href="/authorize?{authorize_qs}">Войти через SSO</a></p>
    <p class="hint">API: {escape(settings.api_base_url)}<br>redirect_uri: {escape(demo_redirect())}</p>
    """
    return HTMLResponse(_page("Mock SSO", body))


def _login_page(*, client_id: str, redirect_uri: str, state: str, error: str | None) -> str:
    options = "\n".join(
        f'<option value="{escape(u.email)}">{escape(u.name)} ({escape(u.email)})</option>'
        for u in SEED_USERS
    )
    err_html = f'<p class="error">{escape(error)}</p>' if error else ""
    body = f"""
    <h1>Mock SSO Login</h1>
    <p class="hint">Выберите тестового пользователя.</p>
    {err_html}
    <form method="post" action="/authorize">
      <input type="hidden" name="client_id" value="{escape(client_id)}">
      <input type="hidden" name="redirect_uri" value="{escape(redirect_uri)}">
      <input type="hidden" name="state" value="{escape(state)}">
      <label>Пользователь
        <select name="email">{options}</select>
      </label>
      <button type="submit">Войти</button>
    </form>
    """
    return _page("Mock SSO Login", body)


@app.get("/authorize", response_class=HTMLResponse)
async def authorize_get(
    client_id: Annotated[str, Query()],
    redirect_uri: Annotated[str, Query()],
    state: Annotated[str, Query()] = "",
    response_type: Annotated[str, Query()] = "code",
) -> HTMLResponse:
    if response_type != "code":
        raise HTTPException(status_code=400, detail="unsupported_response_type")
    if client_id != settings.client_id:
        raise HTTPException(status_code=400, detail="invalid_client_id")
    return HTMLResponse(
        _login_page(client_id=client_id, redirect_uri=redirect_uri, state=state, error=None)
    )


@app.post("/authorize")
async def authorize_post(
    client_id: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    email: Annotated[str, Form()],
    state: Annotated[str, Form()] = "",
) -> RedirectResponse:
    if client_id != settings.client_id:
        raise HTTPException(status_code=400, detail="invalid_client_id")
    code = create_code(email=email, redirect_uri=redirect_uri, client_id=client_id)
    if code is None:
        return HTMLResponse(  # type: ignore[return-value]
            _login_page(
                client_id=client_id,
                redirect_uri=redirect_uri,
                state=state,
                error="Неизвестный пользователь",
            ),
            status_code=400,
        )
    params = {"code": code}
    if state:
        params["state"] = state
    separator = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(
        url=f"{redirect_uri}{separator}{urlencode(params)}",
        status_code=302,
    )


@app.get("/callback", response_class=HTMLResponse)
async def demo_callback() -> HTMLResponse:
    """Built-in demo client page: exchanges code with the Club League API."""
    body = """
    <h1>SSO callback</h1>
    <p id="status">Обмен authorization code…</p>
    <div id="result"></div>
    <p><a href="/">На главную</a></p>
    <script>
      const apiBase = %API_BASE%;
      const statusEl = document.getElementById("status");
      const resultEl = document.getElementById("result");
      const params = new URLSearchParams(window.location.search);
      const code = params.get("code");
      const oauthError = params.get("error");

      function field(label, value) {
        return "<div><dt>" + label + "</dt><dd>" + (value ?? "—") + "</dd></div>";
      }

      async function run() {
        if (oauthError) {
          statusEl.textContent = "Ошибка SSO: " + oauthError;
          statusEl.className = "error";
          return;
        }
        if (!code) {
          statusEl.textContent = "Нет code в query";
          statusEl.className = "error";
          return;
        }
        try {
          const resp = await fetch(apiBase + "/api/auth/sso/callback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code }),
          });
          const body = await resp.json();
          if (!resp.ok) {
            const msg = body?.detail?.error?.message || body?.error?.message || ("HTTP " + resp.status);
            throw new Error(msg);
          }
          const user = body.data.user;
          statusEl.textContent = "Вход выполнен";
          resultEl.innerHTML =
            "<dl>" +
            field("Имя", user.name) +
            field("Email", user.email) +
            field("Роль", user.role) +
            field("can_sudo", String(user.canSudo)) +
            field("clubIds", (user.clubIds || []).join(", ") || "—") +
            "</dl>";
        } catch (err) {
          statusEl.textContent = "Ошибка: " + err.message;
          statusEl.className = "error";
        }
      }
      run();
    </script>
    """
    return HTMLResponse(_page("SSO callback", body.replace("%API_BASE%", _js_str(settings.api_base_url))))


def _js_str(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


@app.post("/token", response_model=TokenResponse)
async def token(
    grant_type: Annotated[str, Form()],
    code: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    client_secret: Annotated[str, Form()],
) -> TokenResponse:
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")
    profile = consume_code(
        code,
        redirect_uri=redirect_uri,
        client_id=client_id,
        client_secret=client_secret,
    )
    if profile is None:
        raise HTTPException(status_code=400, detail="invalid_grant")
    access_token = create_token(profile)
    return TokenResponse(access_token=access_token, expires_in=settings.token_ttl_seconds)


@app.get("/userinfo", response_model=UserinfoResponse)
async def userinfo(authorization: Annotated[str | None, Header()] = None) -> UserinfoResponse:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="invalid_authorization_header")
    token_value = authorization[7:].strip()
    profile = resolve_token(token_value)
    if profile is None:
        raise HTTPException(status_code=401, detail="invalid_token")
    return UserinfoResponse(sub=profile.sub, email=profile.email, name=profile.name)
