# Технологический стек и ограничения

## Backend
- Runtime: Python 3.11+
- Framework: FastAPI
- ORM: SQLAlchemy 2.0 (или Prisma Python)
- Валидация: Pydantic V2 (строго для всех DTO и JSONB-конфигов правил)
- DB: PostgreSQL 15+
- Auth: Интеграция с университетским SSO (OAuth2/SAML)

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