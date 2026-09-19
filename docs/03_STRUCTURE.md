# Структура проекта (Monorepo)

## /apps/api (Backend — FastAPI)

```
apps/api/
  alembic/                      # Alembic migrations
    versions/
      33f25a893516_initial_schema.py
      12541184b6c1_add_audit_logs_seq_identity.py
      a1b2c3d4e5f6_add_calculation_method.py
      b7c8d9e0f1a2_add_display_data.py
      c3d4e5f6a7b8_add_periods.py
  scripts/
    seed_dev_users.py           # Dev: moderator/leader/guest + club
    seed_rules.py               # v2 catalog + default periods + report→period backfill
    verify_audit_chain.py       # Hash chain integrity check
  src/
    main.py                     # FastAPI app, CORS, i18n middleware, error handlers
    api/
      deps.py                   # get_current_user, require_moderator/sudo
      endpoints/
        auth.py                 # POST /auth/sso/callback, POST /auth/refresh
        users.py                # GET /users/me
        reports.py              # CRUD, submit, calculation, comments
        moderation.py           # moderate, dispute, complete, archive
        admin.py                # sudo, sync force/status, rules CRUD, audit list, periods CRUD
        rating.py               # GET /rating (public), GET /periods (public filter)
    core/
      config.py                 # Settings (env), domain whitelist, pool, rate-limit
      database.py               # Async engine/session (NullPool-safe)
      security.py               # JWT create/decode
      errors.py                 # api_error() → { error: { code, message } }
      i18n.py                   # Accept-Language middleware, t() messages
      rate_limit.py             # Configurable in-memory rate limiter
    models/
      entities.py               # SQLAlchemy models (User, Club, Report, AuditLog, …)
      enums.py                  # UserRole, ClubCategory, ReportStatus
    schemas/
      common.py                 # ApiSuccess, ErrorCode
      auth.py                   # SSOLoginDTO, MeResponse, LoginResponse
      report.py                 # CreateReportDTO, UpdateReportDTO, ReportResponse, SetCalculationDTO
      rules.py                  # Pydantic configs for 17 rule types + CombinedCapConfig
      moderation.py             # ModerateReportDTO, DisputeReportDTO
      sudo.py                   # SudoActionDTO, SudoSuccess
      sync.py                   # SyncStatus, SyncQueued, RatingResponse
      criteria.py               # CriteriaOut, RuleOut, AuditLogOut
      period.py                 # PeriodOut, CreatePeriodDTO, UpdatePeriodDTO
      # CommentEntry / CreateCommentDTO live in services/comments_service.py
    services/
      audit_service.py          # Hash chain, AuditService.log/log_sudo_action/verify_chain
      audit_query.py            # Admin audit list query
      auth_service.py           # SSO upsert (email/name only, roles in DB)
      sso_client.py             # OAuth2 code exchange + userinfo
      report_service.py         # CRUD, calculation method, submit, delete
      report_state.py           # State machine transitions
      moderation_service.py     # Approve/dispute/complete + finalPoints
      archive_service.py        # Batch ARCHIVED + auto-complete APPROVED
      auto_complete.py          # Background APPROVED→COMPLETED timer
      rules_engine.py           # 17 rule types calculation
      caps.py                   # G1 combined_cap helper
      global_rules.py           # Load G1 from DB
      rating_caps.py            # Monthly per-criteria caps
      sync_service.py           # Debouncer + rating aggregation
      yandex_sheets.py          # Yandex Disk WebDAV client (CSV overwrite)
      comments_service.py       # Thread from audit_logs + POST comment
      criteria_service.py       # Criteria list + admin rules CRUD
      link_validation.py        # Whitelist domain validation
      periods.py                # Semester → date range fallback (Europe/Moscow)
      period_service.py         # Period CRUD, public list, resolve by activity_date
      sudo_service.py           # force_status / restore_deleted / override_points
      violations_service.py     # access_violations logger
    policies/
      common.py                 # ensure_moderator / ensure_sudo / ensure_club_leader
```

## /apps/mock-sso (Dev OAuth2 provider + demo UI)

```
src/
  main.py    # /authorize, /token, /userinfo, / , /callback
  store.py   # codes/tokens + seed users
  config.py
```

## /apps/swagger (OpenAPI UI)

```
index.html              # Swagger UI (CDN)
nginx.conf.template     # proxy /openapi.json + /api/* → api (same-origin)
Dockerfile
```

Open http://127.0.0.1:8080 after `docker compose up swagger`.

## /apps/web — Frontend (React SPA)

Разработка ведётся на ветке `feat/frontend`. На `feat/backend` может лежать только собранный `dist/` (nginx).
- SSO redirect, report form, moderator queue, public rating (by Period), admin panel (rules + Periods)
- Контракт API: `docs/shared/api-contract.ts`
