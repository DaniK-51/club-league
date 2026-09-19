# AGENTS.md — Club League 2026

> **Read this file first.** It contains non-negotiable constraints and architectural decisions.
> Violating these rules will break the system or produce incorrect point calculations.

## 🎯 Project Overview

**Club League 2026** is a web service for Innopolis University student clubs. It replaces a manual Telegram + Yandex Forms workflow for collecting, validating, and scoring club activity reports.

**Core users:**
- **Club Leaders** (~40 clubs) — submit activity reports with external proof links
- **Moderator** (1 person, @T_Konovalov) — reviews reports, adjusts points, archives periods
- **Guests** — view public rating

**Key principle:** The system is the **single source of truth**. Yandex Disk (WebDAV CSV) is a read-only mirror synced hourly.

---

## 🚫 CRITICAL CONSTRAINTS (NEVER VIOLATE)

### 1. No file uploads — EVER
- Reports accept **external links only** (Google Docs, Telegram, VK, YouTube, Yandex Disk, GitHub, Notion, Dropbox, innopolis.university)
- There is NO file storage in the system. Not even for avatars or attachments.
- If a user asks to "attach a file" — the answer is always "paste a link instead"

### 2. Work with v2 criteria ONLY
- **v2 = 11 common criteria (C1–C11) + 3–4 special criteria per category (Sport/Tech/Art/SI)**
- The old "17 criteria" from `Критерии Лиги клубов 2026 (2).xlsx` is **DEPRECATED**. Do not implement it.
- The phrase "17 действующих критериев" in the internship application is outdated.
- See `/docs/shared/rules-catalog.md` for the authoritative list.

### 3. Audit logs are APPEND-ONLY with hash chain
- Table `audit_logs` has `REVOKE UPDATE, DELETE` at the DB level
- Every row contains `prev_hash` and `hash` (SHA-256)
- **Never** write code that attempts to modify or delete audit records
- **Never** bypass the hash chain logic
- See `/docs/04_ARCHITECTURE.md` for the chain verification algorithm

### 4. Moderator is NEVER a club leader
- These roles are mutually exclusive by design
- A moderator cannot approve their own club's reports (even if they somehow got both roles)
- The `users` table enforces this at the application level

### 5. 7-day deadline is a SOFT WARNING, not a block
- Leaders CAN submit overdue reports
- The system only shows a yellow warning: "This date looks unusual. Are you sure?"
- **No automatic penalties**, no automatic reminders, no blocking

### 6. All times are Europe/Moscow (UTC+3)
- Deadline calculations, date comparisons, `activity_date` validation — all in Moscow time
- Store as UTC in DB, convert at the boundary

### 7. i18n is mandatory (RU/EN)
- All UI strings must be translated
- All criteria names have `name_ru` and `name_en` in DB
- Use `i18next` on frontend, `gettext` or similar on backend

---

## 🏗️ Architecture Overview

### Stack
- **Backend:** Python 3.11+ / FastAPI / SQLAlchemy 2.0 async / PostgreSQL 16
- **Frontend:** React 18 + Vite (SPA, **NOT Next.js**) / TypeScript strict / Tailwind + shadcn/ui
- **Auth:** University SSO only (OAuth2/SAML). No local passwords. Dev: `apps/mock-sso`.
- **Validation:** Pydantic V2 (strict mode) on backend, Zod on frontend
- **Package manager:** uv (backend) / npm (frontend)

### Report State Machine (8 statuses)
```
DRAFT → ON_MODERATION → APPROVED → COMPLETED → ARCHIVED
                ↓              ↓
        CHANGES_REQUIRED    DISPUTED → (back to ON_MODERATION or APPROVED)
                ↓
              CLOSED → ARCHIVED
```

**Key rules:**
- Only `COMPLETED` reports count toward rating
- `ARCHIVED` is immutable and batch-triggered by moderator
- `DISPUTED` has no auto-timer — moderator responds manually
- Sudo mode can force ANY transition (with mandatory `reason`)

### Rules Engine
- Hybrid storage: normalized columns + `JSONB` for rule configs
- Configs validated by Pydantic schemas per `rule_type`
- **17 rule types** implemented (tiered, scale, binary, tiered_with_bonus, per_unit_with_bonus, binary_with_monthly_cap, fixed_monthly_with_per_unit, scale_with_frequency_limit, scale_with_conditional_bonus, scale_with_league_bonus, scale_with_conditional_modifier, scale_split_mode, binary_scale, per_person_per_month, discretionary, fixed_per_event_with_monthly_cap, combined_cap)
- **27 criteria** seeded (C1–C11, S1–S4, T1–T3, A1–A4, I1–I4, G1)
- **Combined cap G1:** `C4 + C5 ≤ 15% of monthly total` — applied per month, loaded from DB
- **Monthly caps** (C4, C7, C9, C11) applied per month before G1
- **Manual override:** Moderator can set ANY `final_points` value (logged in audit)
- **calculationMethod:** `auto` (RulesEngine) or `manual` (moderator sets `manualPoints`)

### Yandex Disk WebDAV Sync
- **Event-driven with 1-hour debounce**
- Full rating recalculation on every sync
- Export: CSV overwrite via WebDAV (`https://webdav.yandex.ru`) — Basic auth (login + application password)
- Yandex is **read-only mirror** — never write from Yandex back to our DB
- Retry with exponential backoff, fallback to manual export

---

## 📐 Code Standards

### Python (Backend)
- **Strict typing everywhere.** No `Any`, no untyped dicts.
- Use Pydantic V2 models for all DTOs and JSONB configs
- One module = one responsibility (see `/docs/03_STRUCTURE.md`)
- All business logic changes MUST trigger `AuditService.log()`
- Use `policy-based` authorization — see `/app/policies/`
- Timezone: always use `zoneinfo.ZoneInfo("Europe/Moscow")` for business logic

### TypeScript (Frontend)
- `strict: true` in tsconfig, no `any`, no `@ts-ignore`
- All API types imported from `/docs/shared/api-contract.ts`
- Use TanStack Query for data fetching, Zustand for local state
- All user-visible strings via `useTranslation()` hook
- Forms: react-hook-form + zod validation

### Database
- Use Prisma schema (`/docs/shared/schema.prisma`) as the source of truth
- Every migration must be reviewed for audit-log implications
- Never `DROP` or `TRUNCATE` tables in production migrations
- Indexes required on: `audit_logs(entity_type, entity_id)`, `reports(club_id, status)`, `report_links(url)`

---

## 🔐 Security Rules

1. **Rate limiting** is configurable via admin panel (not hardcoded)
2. **Link validation:** whitelist-only, checked at `POST /api/reports`
3. **Sudo actions** require:
   - `can_sudo = true` on user
   - Mandatory `reason` field (non-empty string)
   - Logged in BOTH `audit_logs` AND `sudo_actions` tables
4. **Access violations** logged in `access_violations` table
5. **No direct DB access** bypassing the application layer (enforced by DB roles)

---

## 🧪 Testing Requirements

### Mandatory
- **Unit tests** for every rule type in `RulesEngine` (≥80% coverage)
- **Policy tests** for every authorization scenario
- **State machine tests** for every valid AND invalid transition
- **Hash chain verification test** (run in CI)

### Nice to have
- Property-based tests (Hypothesis) for combined caps
- Integration tests with testcontainers for PostgreSQL
- E2E tests with Playwright for critical user flows

### NOT required
- ❌ Regression tests on historical data (old 17-criteria system is deprecated)
- ❌ Load testing for MVP (40 clubs, 200 reports/month is trivial)

---

## 📚 Documentation Map

| File | Purpose |
|------|---------|
| `/README.md` | Project overview + local setup |
| `/docs/01_PRODUCT_BRIEF.md` | User stories, MVP scope |
| `/docs/02_TECH_STACK.md` | Stack + architectural constraints |
| `/docs/03_STRUCTURE.md` | Monorepo folder layout |
| `/docs/04_ARCHITECTURE.md` | Mermaid diagrams (state machine, flows) |
| `/docs/05_IMPLEMENTATION_PLAN.md` | Step-by-step dev plan + DoD |
| `/docs/06_AUDIT.md` | **Audit system: hash chain, actions, displayData, API** |
| `/docs/shared/schema.prisma` | Database schema (source of truth) |
| `/docs/shared/api-contract.ts` | API DTOs, responses, error codes |
| `/docs/shared/rules-catalog.md` | **v2 criteria catalog — THE rulebook** |

**Before writing any feature:** read the relevant doc. Do not guess business rules.

---

## ⚠️ Common Pitfalls

### ❌ DO NOT
- Hardcode point values (e.g., `if criteria == 'C1': return 400`). Use `RulesEngine` with configs from DB.
- Assume a report has only one link. Reports have **multiple** links in `report_links` table.
- Calculate rating on every page load. Use cached rating, invalidate on `COMPLETED` changes.
- Send email/Telegram notifications for deadlines. We explicitly don't do this.
- Allow leaders to delete reports after submission. Only `DRAFT` can be soft-deleted.
- Mix up `calculated_points` (from engine) and `final_points` (after moderator override).
- Forget to include `prev_hash` when creating audit log entries.
- Use `datetime.now()` without timezone. Always use `datetime.now(ZoneInfo("Europe/Moscow"))`.

### ✅ ALWAYS
- Check policy authorization BEFORE business logic
- Log to `audit_logs` for ANY state change or point modification
- Validate links against whitelist BEFORE saving
- Return `{ data: T } | { error: { code, message } }` from all API endpoints
- Use `ErrorCode` enum from `api-contract.ts` for error responses
- Include both `name_ru` and `name_en` when creating new criteria

---

## 📝 Commit Messages (Conventional Commits)

All commits MUST follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.
This is **non-negotiable** — CI will reject non-conforming messages.

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | When to use | Example |
|------|-------------|---------|
| `feat` | New feature or capability | `feat(reports): add report submission form` |
| `fix` | Bug fix | `fix(rules): correct combined cap calculation` |
| `refactor` | Code change that neither fixes a bug nor adds a feature | `refactor(audit): extract hash chain to service` |
| `docs` | Documentation only | `docs: update rules-catalog with C11 details` |
| `test` | Adding or updating tests | `test(rules): add unit tests for tiered type` |
| `chore` | Build, CI, dependencies, tooling | `chore: add eslint config` |
| `style` | Formatting, whitespace, semicolons (no logic change) | `style(frontend): fix indentation in ReportForm` |
| `perf` | Performance improvement | `perf(rating): add index on reports.club_id` |
| `ci` | CI/CD pipeline changes | `ci: add GitHub Actions workflow` |
| `build` | Build system or external dependencies | `build: upgrade fastapi to 0.115` |

### Scopes

Use one of these scopes (matches `/docs/03_STRUCTURE.md`):

| Scope | Covers |
|-------|--------|
| `reports` | Report CRUD, submission, links validation |
| `rules` | RulesEngine, rule types, Pydantic configs |
| `moderation` | Status transitions, approve/reject/dispute |
| `rating` | Rating calculation, caching, public page |
| `sync` | Yandex Disk WebDAV sync, debouncer, retry, rating |
| `audit` | Audit logs, hash chain, sudo actions |
| `auth` | SSO integration, JWT, policies |
| `frontend` | React components, forms, i18n |
| `admin` | Admin panel, rules management |
| `db` | Migrations, schema changes, indexes |
| `docs` | Documentation files |
| `infra` | Docker, env, deployment |

### Rules

1. **Description** is lowercase, no period at the end
   - ✅ `feat(reports): add whitelist domain validation`
   - ❌ `feat(reports): Add whitelist domain validation.`

2. **Body** is required when:
   - The commit implements a step from `05_IMPLEMENTATION_PLAN.md` → reference the step number
   - The commit changes business logic → explain WHY
   - The commit fixes a bug → describe the root cause

3. **Footer** for breaking changes:
   ```
   BREAKING CHANGE: removed `preview_points` field from ReportResponse
   ```

4. **One logical change per commit.** Do not bundle unrelated changes.

5. **Link to plan step** in body when applicable:
   ```
   feat(rules): implement tiered and scale rule types

   Implements Backend Step 4 from 05_IMPLEMENTATION_PLAN.md.
   Adds Pydantic schemas for TieredConfig and ScaleConfig.
   Unit tests cover boundary values and empty tiers.
   ```

### Examples

**Good:**
```
feat(reports): add soft deadline warning for overdue reports

Frontend Step 3. Shows yellow badge when activity_date + 7 days < today.
No blocking — leader can still submit.
```

```
fix(rules): prevent division by zero in combined cap

When total monthly points = 0, combined cap now returns 0
instead of raising ZeroDivisionError.
```

```
docs: fix DISUDTED typo in state machine diagram
```

```
test(audit): add hash chain integrity verification test
```

**Bad:**
```
update code                    ← no type, no scope, vague
fix bug                        ← no scope, no description of what bug
feat: add everything           ← too broad, multiple changes
WIP                            ← not conventional
reports: add form              ← missing type
feat(Reports): Add Form        ← wrong case
```

### For AI Agents

When generating commits:
1. Always use the format above — no exceptions
2. Reference the step number from `05_IMPLEMENTATION_PLAN.md` in the body
3. Keep description under 72 characters
4. If you changed multiple scopes, split into multiple commits
5. Never use `git commit -m "update"` or similar vague messages

---

## 🔄 Workflow for Agents

1. **Before coding:** Read relevant `/docs/` file + this AGENTS.md
2. **Before committing:** Run linter + type checker + tests
3. **Before adding a feature:** Check if it violates any 🚫 constraint above
4. **When in doubt:** Ask the human. Do not invent business rules.
5. **After completing a step:** Update `/docs/05_IMPLEMENTATION_PLAN.md` checkbox

---

## 📞 Escalation

If you encounter a contradiction between this file and other docs:
- **This file wins** for architectural constraints
- **`/docs/shared/rules-catalog.md` wins** for point values and rule logic
- **Ask the human** for anything else

---

*Last updated: 2026-09-19*
*Maintainer: @T_Konovalov (mentor)*
