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
docker compose up --build
```

Поднимает:
| Сервис | URL | Описание |
|--------|-----|----------|
| `db` | `localhost:5432` | PostgreSQL 16 |
| `mock-sso` | `http://127.0.0.1:9001` | Dev OAuth2 SSO |
| `api` | `http://127.0.0.1:8000` | FastAPI (миграции + seed при старте) |

Проверка: `curl http://127.0.0.1:8000/health`

### Тестовые пользователи mock SSO
Роли и `can_sudo` хранятся **только в БД API**, не в SSO.

| email | после seed |
|-------|------------|
| `moderator@innopolis.university` | MODERATOR + can_sudo |
| `leader@innopolis.university` | CLUB_LEADER + Dev Sport Club |
| `guest@innopolis.university` | GUEST |

### Проверка SSO в браузере
Откройте **http://127.0.0.1:9001/** → «Войти через SSO» → выберите пользователя.
Страница `/callback` сама отправит `code` в `POST /api/auth/sso/callback` и покажет роль из нашей БД.

### Hot-reload разработка (вне Docker)

```bash
docker compose up -d db mock-sso

cd apps/api
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m scripts.seed_dev_users
uv run uvicorn src.main:app --reload --port 8000
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

## 📞 Контакты
- Ментор: Тимофей Коновалов (@T_Konovalov)
