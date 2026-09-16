# Mock SSO (dev only)

OAuth2 authorization-code provider + built-in demo UI for Club League.

**Roles and `can_sudo` are NOT here** — only `sub`, `email`, `name`.

## Run

```bash
cd apps/mock-sso
uv sync
uv run uvicorn src.main:app --port 9001
```

Open **http://127.0.0.1:9001/** → «Войти через SSO» → pick a user → callback page exchanges `code` with the API and shows role from our DB.

## Test users

| email | name | sub |
|-------|------|-----|
| moderator@innopolis.university | Тимофей Модератор | sso-mod-1 |
| leader@innopolis.university | Лидер Клуба | sso-leader-1 |
| guest@innopolis.university | Гость | sso-guest-1 |

## Env

| Var | Default | Meaning |
|-----|---------|---------|
| `CLIENT_ID` | `club-league-dev` | OAuth client |
| `CLIENT_SECRET` | `club-league-dev-secret` | OAuth secret |
| `SELF_BASE_URL` | `http://127.0.0.1:9001` | This service (browser) |
| `API_BASE_URL` | `http://127.0.0.1:8000` | Club League API (browser callback page) |

## Endpoints

- `GET /` — demo landing + login button
- `GET/POST /authorize` — login form (OAuth2)
- `GET /callback` — demo client: `POST {API}/api/auth/sso/callback` and render user
- `POST /token` — exchange code
- `GET /userinfo` — `{ sub, email, name }`
- `GET /health`

## Client credentials

- `client_id`: `club-league-dev`
- `client_secret`: `club-league-dev-secret`
- demo `redirect_uri`: `http://127.0.0.1:9001/callback` (must match API `SSO_REDIRECT_URI`)
