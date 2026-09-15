# Структура проекта (Monorepo)

## /apps/api (Backend - FastAPI)
src/
  api/
    endpoints/
      reports.py
      rating.py
      admin.py
  core/
    config.py          # Настройки, whitelist доменов
    security.py        # SSO интеграция, Sudo проверки
  models/              # SQLAlchemy модели
  schemas/             # Pydantic DTO и схемы для JSONB правил
  services/
    rules_engine.py    # Ядро расчёта баллов (17 типов правил)
    sync_service.py    # Debouncer и Yandex Sheets API клиент
    audit_service.py   # Логирование с hash chain
  policies/            # RBAC логика (ReportPolicy, ClubPolicy)
  main.py

## /apps/web (Frontend - React/Vite)
src/
  app/
    (auth)/login/      # SSO редирект
    (leader)/reports/  # Форма создания отчёта (с soft warning дедлайна)
    (moderator)/queue/ # Дашборд модерации
    (public)/rating/   # Публичный рейтинг
  components/
    ui/                # shadcn/ui
    reports/ReportForm.tsx
    rating/RatingTable.tsx
  lib/
    api-client.ts      # Fetch обёртка с типами из api-contract
    i18n.ts            # Конфигурация ru/en
  hooks/
    useReportSubmission.ts
  store/
    auth.store.ts