# 🏆 Club League 2026 (Лига Клубов)

Единый веб-сервис для сбора, валидации, автоматического расчёта и модерации отчётов о деятельности студенческих клубов Университета Иннополис. Заменяет ручной процесс через Telegram и Яндекс.Формы.

## 📚 Документация

Вся архитектура, контракты и план разработки находятся в папке `/docs`:
- [`01_PRODUCT_BRIEF.md`](./docs/01_PRODUCT_BRIEF.md) — Цели, пользовательские истории, границы MVP.
- [`02_TECH_STACK.md`](./docs/02_TECH_STACK.md) — Технологический стек и архитектурные ограничения.
- [`03_STRUCTURE.md`](./docs/03_STRUCTURE.md) — Структура монорепо (Frontend + Backend).
- [`04_ARCHITECTURE.md`](./docs/04_ARCHITECTURE.md) — Диаграммы потоков данных и State Machine.
- [`05_IMPLEMENTATION_PLAN.md`](./docs/05_IMPLEMENTATION_PLAN.md) — Пошаговый план имплементации и DoD.
- [`shared/schema.prisma`](./docs/shared/schema.prisma) — Единая схема базы данных.
- [`shared/api-contract.ts`](./docs/shared/api-contract.ts) — TypeScript-контракт API (DTO, Responses, Error Codes).
- [`shared/rules-catalog.md`](./docs/shared/rules-catalog.md) — **Полный каталог 17+ типов правил, капов и лимитов (v2)**.

## 🚀 Local Development

### Предварительные требования
- Docker & Docker Compose (основной путь)
- Для hot-reload разработки: Python 3.11+ и [uv](https://docs.astral.sh/uv/)

### Быстрый старт (Docker, весь стек)

```bash
cp .env.example .env   # при необходимости поправь порты/секреты
docker compose up --build
```

Поднимает:
| Сервис | URL (по умолчанию) | Описание |
|--------|-----|----------|
| `db` | `localhost:${DB_PORT:-5432}` | PostgreSQL 16 |
| `mock-sso` | `http://127.0.0.1:${MOCK_SSO_PORT:-9001}` | Dev OAuth2 SSO |
| `api` | `http://127.0.0.1:${API_PORT:-8000}` | FastAPI (миграции + seed при старте) |
| `swagger` | `http://127.0.0.1:${SWAGGER_PORT:-8080}` | OpenAPI UI (Swagger) |

### Конфигурация через `.env`

Два уровня — без дублирования:

| Файл | Что в нём |
|------|-----------|
| **`.env`** (корень) | Только compose: порты, Postgres, shared SSO-creds |
| **`apps/api/.env`** | Все настройки приложения (JWT, SSO URLs, Yandex, rate-limit…) |

В Docker compose загружает `apps/api/.env` через `env_file` и **переопределяет** только хосты для in-cluster сети:
- `DATABASE_URL` → `@db:5432`
- `SSO_TOKEN_URL` / `SSO_USERINFO_URL` → `http://mock-sso:9001/...`

| Переменная (корневой `.env`) | По умолчанию | Назначение |
|------------|-------------|------------|
| `API_PORT` | `8000` | Порт FastAPI |
| `DB_PORT` | `5432` | Порт PostgreSQL |
| `MOCK_SSO_PORT` | `9001` | Порт mock SSO |
| `SWAGGER_PORT` | `8080` | Порт Swagger UI |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `club_league` | Учётка БД |
| `SSO_CLIENT_ID` / `SSO_CLIENT_SECRET` | `club-league-dev` | OAuth2 client (shared) |

См. `apps/api/.env.example` — полный список настроек приложения.

### Тестовые пользователи mock SSO
Роли и `can_sudo` хранятся **только в БД API**, не в SSO.

| email | после seed |
|-------|------------|
| `moderator@innopolis.university` | MODERATOR + can_sudo |
| `leader@innopolis.university` | CLUB_LEADER + Dev Sport Club |
| `guest@innopolis.university` | GUEST |

### Проверка SSO в браузере
Откройте **http://127.0.0.1:${MOCK_SSO_PORT:-9001}/** → «Войти через SSO» → выберите пользователя.
Страница `/callback` сама отправит `code` в `POST /api/auth/sso/callback` и покажет роль из нашей БД.

### Hot-reload разработка (вне Docker)

```bash
docker compose up -d db mock-sso

cd apps/api
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m scripts.seed_dev_users
uv run uvicorn src.main:app --reload --port ${API_PORT:-8000}
```

Тесты и линт:
```bash
cd apps/api && uv run pytest && uv run ruff check src tests scripts
cd apps/mock-sso && uv run pytest
```

## 🛡️ Безопасность и Аудит
- Все действия логируются в `audit_logs` с криптографической цепочкой (hash chain).
- Прямые `UPDATE`/`DELETE` к таблице аудита запрещены на уровне БД (`REVOKE`).
- Sudo-действия требуют обязательного поля `reason` и отдельного логирования.

## 📊 Yandex Disk WebDAV (rating file mirror)

Система — source of truth. На Диск выгружается **CSV-файл** рейтинга (overwrite).

```
Base: https://webdav.yandex.ru/
Auth: Basic (Yandex login + application password, 16 символов)
PUT   club-league/rating.csv
MKCOL club-league/   (если папки нет)
```

```bash
# apps/api/.env
YANDEX_SHEETS_ENABLED=true
YANDEX_WEBDAV_USERNAME=<логин Яндекса>
YANDEX_WEBDAV_PASSWORD=<application password, 16 символов>
YANDEX_DISK_PATH=club-league/rating.csv
```

- Debounce **1 час** после COMPLETED; force: `POST /api/admin/sync/force`
- Статус: `GET /api/admin/sync/status`
- Публичный источник: `GET /api/rating`
- Dev: `YANDEX_SHEETS_ENABLED=false` → NullYandexClient

## 📞 Контакты
- Ментор: Тимофей Коновалов (@T_Konovalov)
