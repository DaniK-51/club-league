# Технологический стек и ограничения

## Backend
- Runtime: Python 3.11+
- Package manager: **[uv](https://docs.astral.sh/uv/)** — единственный способ управления зависимостями (`uv sync`, `uv run …`). Не использовать `pip`/`venv`/`requirements.txt` вручную.
- Framework: FastAPI
- ORM: SQLAlchemy 2.0 (async)
- Миграции: **Alembic** (`alembic upgrade head`). `schema.prisma` — источник истины для схемы, но runtime-миграции — Alembic.
- Валидация: Pydantic V2 (строго для всех DTO и JSONB-конфигов правил)
- DB: PostgreSQL 16 (Docker Compose, `localhost:5432`)
- Auth: University SSO (OAuth2) in prod. **Dev:** `apps/mock-sso` (same client path). SSO returns **only** `sub`/`email`/`name` — `role` and `can_sudo` live **only in our DB**.

## Frontend
- Framework: React 18 + Vite (SPA, без Next.js SSR)
- Language: TypeScript (strict: true, запрет `any`)
- State & Data: TanStack Query v5, Zustand
- UI & Forms: Tailwind CSS, shadcn/ui, react-hook-form + zod
- i18n: i18next (полная поддержка RU/EN)

## Инфраструктура и интеграции
- Yandex Sheets API: для синхронизации рейтинга (debounce 1 час, retry с exponential backoff).
- Часовой пояс: Все дедлайны и сравнения дат строго в `Europe/Moscow` (UTC+3).

## Архитектурные правила
1. **Движок правил:** Гибридный. Нормализованные таблицы для связей + `JSONB` для конфигурации правил (валидируется Pydantic-схемами по `rule_type`).
2. **Безопасность:** Таблица `audit_logs` имеет права `REVOKE UPDATE, DELETE`. Каждая запись содержит `prev_hash` и `hash` (SHA-256).
3. **API Contract:** Все ответы в формате `{ data: T } | { error: { code, message } }`.
4. **Sudo mode:** Требует обязательного поля `reason` и логируется в отдельную таблицу `sudo_actions`.