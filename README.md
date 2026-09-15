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
- PostgreSQL 15+ (локально или через Docker)
- Docker & Docker Compose (опционально, для БД)

### 1. Поднятие базы данных
```bash
# Запуск PostgreSQL через Docker
docker run --name club-league-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=club_league -p 5432:5432 -d postgres:15
```

### 2. Backend (`/apps/api`)
```bash
cd apps/api
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows
pip install -r requirements.txt

# Копирование env
cp .env.example .env
# (Отредактируйте .env, указав DATABASE_URL="postgresql://postgres:postgres@localhost:5432/club_league")

# Применение миграций (Alembic или Prisma)
prisma db push # или alembic upgrade head

# Запуск сервера разработки
uvicorn src.main:app --reload --port 8000
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
