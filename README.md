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
- Node.js 20+ и Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker & Docker Compose

### 1. Поднятие базы данных
```bash
docker compose up -d
# PostgreSQL 16 на localhost:5432 (user/pass/db: club_league)
```

### 2. Backend (`/apps/api`)
```bash
cd apps/api
cp .env.example .env

uv sync
uv run alembic upgrade head
uv run uvicorn src.main:app --reload --port 8000
```

Проверка: `curl http://127.0.0.1:8000/health`

Тесты и линт:
```bash
uv run pytest
uv run ruff check src tests
```


### 3. Frontend (`/apps/web`)
```bash
cd apps/web
npm install

# Копирование env
cp .env.example .env.local

# Запуск сервера разработки
npm run dev
```

## 🛡️ Безопасность и Аудит
- Все действия логируются в `audit_logs` с криптографической цепочкой (hash chain).
- Прямые `UPDATE`/`DELETE` к таблице аудита запрещены на уровне БД (`REVOKE`).
- Sudo-действия требуют обязательного поля `reason` и отдельного логирования.

## 📞 Контакты
- Ментор: Тимофей Коновалов (@T_Konovalov)
