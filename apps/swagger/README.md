# Swagger UI for Club League API

Standalone OpenAPI browser for `apps/api`.

## Run

```bash
docker compose up -d swagger
# open http://127.0.0.1:8080
```

- Serves Swagger UI (CDN assets)
- Proxies `/openapi.json` → `http://api:8000/openapi.json`
- Try-it-out uses `http://127.0.0.1:8000` (browser → host-mapped API)

## Auth in Swagger

1. `POST /api/auth/sso/callback` with a code from mock SSO
2. Copy `data.accessToken`
3. Click **Authorize** → `Bearer <token>`
