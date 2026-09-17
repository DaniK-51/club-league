# Swagger UI for Club League API

Standalone OpenAPI browser for `apps/api`.

## Run

```bash
docker compose up -d swagger
# open http://127.0.0.1:${SWAGGER_PORT:-8080}
```

- Serves Swagger UI (CDN assets)
- Proxies `/openapi.json` and `/api/*` → `http://api:${API_PORT}/...`
- Same-origin — no CORS for Try-it-out

## Auth in Swagger

1. `POST /api/auth/sso/callback` with a code from mock SSO
2. Copy `data.accessToken`
3. Click **Authorize** → `Bearer <token>`

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `API_HOST` | `api` | Upstream API hostname (in-cluster) |
| `API_PORT` | `8000` | Upstream API port |
