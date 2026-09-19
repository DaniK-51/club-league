# План имплементации MVP

## Backend (/apps/api)
- [x] **Шаг 1:** Инициализация FastAPI, SQLAlchemy, подключение к PostgreSQL. Настройка миграций (Alembic) по `schema.prisma`.
- [x] **Шаг 2:** Интеграция SSO (OAuth2/SAML) + Policy-based авторизация (модуль `policies/`). Dev: `apps/mock-sso` (roles/sudo only in our DB).
- [x] **Шаг 3:** Реализация `AuditService` с криптографической цепочкой (hash chain) и триггерами БД (REVOKE). `seq` identity + advisory lock; verify script.
- [x] **Шаг 4:** Ядро `RulesEngine`: все 17 типов правил из rules-catalog.md (tiered, scale, binary, tiered_with_bonus, per_unit_with_bonus, binary_with_monthly_cap, fixed_monthly_with_per_unit, scale_with_frequency_limit, scale_with_conditional_bonus, scale_with_league_bonus, scale_with_conditional_modifier, scale_split_mode, binary_scale, per_person_per_month, discretionary, fixed_per_event_with_monthly_cap, combined_cap) + валидация JSONB через Pydantic. Seed: 27 критериев v2.
- [x] **Шаг 5:** Полный CRUD отчётов (`reports.py`) с валидацией whitelist ссылок и soft warning дедлайна (7 дней).
- [x] **Шаг 6:** Логика модерации: переходы статусов, расчёт `finalPoints`, применение капов (включая combined cap C4+C5).
- [x] **Шаг 7:** Sudo mode: форсированные переходы и восстановление удалённых отчётов с обязательным `reason`.
- [x] **Шаг 8:** Sync Service: Debouncer (1 час) + клиент Yandex Disk WebDAV с retry логикой. Public rating + monthly caps + G1.
- [x] **Шаг 9 (frontend requests):** Report detail API — `reportData` в response, moderator edit, `POST /comments`, тред из audit.
- [x] **Шаг 10 (frontend requests):** Calculation method — `PATCH /api/reports/:id/calculation` (auto/manual + manualPoints + reason).
- [x] **Шаг 11 (frontend requests):** Audit `display_data` JSONB + enrichment (camelCase keys for frontend).
- [x] **Шаг 12 (frontend requests):** Periods — entity + CRUD `/admin/periods`, assignment by `activity_date`, `periodName`, rating/archive by Period; approve без comment при `calculation_method=manual`.
- [x] **Шаг 13 (frontend requests):** Public `GET /api/periods` (без auth, active+archived) + rating считает COMPLETED+ARCHIVED (архивный период не пустеет).

### Known backend gaps (not blockers for MVP)
- Rate limiter in-memory (not multi-instance).
- `YANDEX_SHEETS_ENABLED` env name is legacy; client is WebDAV CSV.
- `POST /admin/sync/force` accepts `semester` but flush uses current Period.
- C7 frequency limit approximated as monthly point cap.
- InnoHasle API — post-MVP.
- Own-club moderator check intentionally **not** enforced (product decision).
- i18n infrastructure present; UI language currently English-first.

## Frontend (/apps/web)
Source on `feat/frontend` (this branch may only carry built `dist/`).
- [x] **Шаг 1:** Инициализация Vite + React + Tailwind + shadcn/ui. Настройка i18next (RU/EN).
- [x] **Шаг 2:** Настройка `api-client.ts` и TanStack Query. Интеграция SSO редиректа.
- [x] **Шаг 3:** Форма создания отчёта для лидера: динамические поля по типу критерия, валидация ссылок, модальное окно "Странная дата" (soft warning).
- [x] **Шаг 4:** Дашборд модератора: список отчётов, бейджи просрочки, interface изменения баллов. Comment обязателен для CHANGES_REQUIRED и auto-override; **не** обязателен при `calculationMethod=manual` (points уже через PATCH /calculation).
- [x] **Шаг 5:** Публичная страница рейтинга (`/rating`) с фильтрацией по **периодам** (`GET /api/periods` public + `GET /api/rating?period=`), включая архивные.
- [x] **Шаг 6:** Админ-панель: аудит, force sync, rules CRUD (JSONB), **вкладка Periods** (create/edit/delete/archive).
- [x] **Шаг 7 (periods frontend):** Типы + `api-client` + hooks для Periods; вкладка Periods в админке; archive dialog с выбором периода; `periodName` на карточках; рейтинг `?period=`.

## Правила выполнения (для ИИ-агента)
1. Один шаг = один промпт. Не генерировать код для следующих шагов.
2. Перед написанием логики всегда определять TypeScript интерфейсы и Pydantic схемы.
3. Запрещено использование `any` в TS и сырых словарей `dict` без типизации в Python.
4. Любое изменение статуса или баллов **обязательно** должно вызывать `AuditService`.

# DoD (Definition of Done) для каждого шага

- [ ] Код компилируется без ошибок TypeScript (`strict: true`) и Pydantic validation ошибок.
- [ ] ESLint + Ruff/Black проходят без предупреждений.
- [ ] Покрытие тестами `RulesEngine` (Unit-тесты для каждого типа правила) ≥ 80%.
- [ ] API строго соответствует `api-contract.ts` (ни одного лишнего поля в ответе).
- [ ] В таблице `audit_logs` успешно проверяется целостность хеш-цепочки (скрипт верификации проходит).
- [ ] Whitelist ссылок корректно блокирует недопустимые домены на этапе `POST /api/reports`.
- [ ] Отсутствуют `console.log` и захардкоженные магические числа (вынесены в конфиг).