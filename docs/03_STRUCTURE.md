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
    rules_engine.py    # Ядро расчёта баллов (17 типов правил, v2 catalog)
    sync_service.py    # Debouncer и Yandex Disk WebDAV клиент
    audit_service.py   # Логирование с hash chain
    comments_service.py # Тред комментариев из audit_logs
    archive_service.py # Batch ARCHIVED + auto-complete APPROVED
    rating_caps.py     # Месячные капы
    global_rules.py    # G1 combined_cap из DB
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

## /apps/swagger (OpenAPI UI)

```
index.html     # Swagger UI (CDN)
nginx.conf     # proxy /openapi.json → api:8000
Dockerfile
```

Open http://127.0.0.1:8080 after `docker compose up swagger`.