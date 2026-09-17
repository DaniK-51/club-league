# Система аудита — Club League 2026

Полная документация по системе аудит-логов: модель данных, хеш-цепочка, типы действий, защита, API и верификация.

---

## 1. Назначение

Система аудита — **единственный источник правды** о том, кто, когда и что изменил в системе. Каждое изменение статуса, баллов, правил или данных отчёта записывается в `audit_logs` и не может быть изменено или удалено.

**Ключевые принципы:**
- Append-only — записи только добавляются
- Криптографическая целостность — SHA-256 хеш-цепочка
- Полная прослеживаемость — от создания отчёта до архивации
- Комментарии как GitHub Issues — тред извлекается из аудита без отдельной таблицы

---

## 2. Модель данных

### 2.1. Таблица `audit_logs`

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | UUID | Уникальный идентификатор записи |
| `seq` | BIGINT IDENTITY | Монотонный порядок цепочки (генерируется БД) |
| `prev_hash` | VARCHAR(64) | SHA-256 предыдущей записи (genesis = 64 нуля) |
| `hash` | VARCHAR(64) | SHA-256 текущей записи |
| `entity_type` | VARCHAR(64) | Тип сущности: `report`, `user`, `rule` |
| `entity_id` | VARCHAR(64) | Идентификатор сущности |
| `action` | VARCHAR(64) | Действие (см. раздел 4) |
| `old_value` | JSONB | Состояние до изменения (nullable) |
| `new_value` | JSONB | Состояние после изменения (nullable) |
| `performed_by_id` | UUID FK→users | Кто выполнил действие |
| `performed_by_role` | VARCHAR(32) | Роль на момент действия |
| `performed_at` | TIMESTAMPTZ | Время действия (UTC) |
| `reason` | TEXT | Комментарий/причина (nullable, обязателен для sudo) |

**Индексы:**
- `ix_audit_logs_seq` — уникальный, для порядка цепочки
- `ix_audit_logs_entity` — `(entity_type, entity_id)` для выборки по сущности
- `ix_audit_logs_performed_at` — для временных запросов

### 2.2. Таблица `sudo_actions`

Отдельный лог для sudo-действий (дублируется в `audit_logs` с `action="sudo_action"`).

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | UUID | Идентификатор |
| `performed_by_id` | UUID FK→users | Модератор с `can_sudo=true` |
| `action` | VARCHAR(64) | `force_status`, `restore_deleted`, `override_points` |
| `entity_type` | VARCHAR(64) | Тип сущности |
| `entity_id` | VARCHAR(64) | Идентификатор сущности |
| `old_value` | JSONB | Состояние до |
| `new_value` | JSONB | Состояние после |
| `reason` | TEXT | **Обязательная** причина |
| `performed_at` | TIMESTAMPTZ | Время |

### 2.3. Таблица `access_violations`

Лог попыток доступа без прав (403).

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | UUID | Идентификатор |
| `user_id` | UUID FK→users, nullable | Кто попытался (null для анонимных) |
| `path` | VARCHAR(512) | Путь запроса |
| `method` | VARCHAR(16) | HTTP-метод |
| `detail` | TEXT | Описание нарушения |
| `occurred_at` | TIMESTAMPTZ | Время |

---

## 3. Хеш-цепочка (Hash Chain)

### 3.1. Алгоритм

Каждая запись содержит SHA-256 хеш, вычисленный из всех полей записи + хеш предыдущей записи.

```
hash_n = SHA256(canonical_json({
    prev_hash:      hash_{n-1},
    entity_type:    "report",
    entity_id:      "uuid",
    action:         "status_changed",
    old_value:      {...},
    new_value:      {...},
    performed_by_id: "uuid",
    performed_by_role: "MODERATOR",
    performed_at:   "2026-09-17T22:00:00+00:00",
    reason:         "optional comment"
}))
```

**Genesis** (первая запись): `prev_hash = "0000...0000"` (64 нуля).

### 3.2. Canonical JSON

Для детерминированного хеширования JSON сериализуется с:
- Сортировкой ключей (`sort_keys=True`)
- Разделителями `(",", ":")` (без пробелов)
- `ensure_ascii=False` (Unicode как есть)
- `default=str` (для datetime и других типов)

### 3.3. Порядок цепочки

Порядок определяется колонкой `seq` (BIGINT IDENTITY, генерируется PostgreSQL). Это гарантирует монотонный порядок даже при конкурентных записях.

**Защита от fork:** перед чтением последнего хеша берётся advisory lock:
```sql
SELECT pg_advisory_xact_lock(hashtext('club_league_audit_chain'))
```
Это сериализует конкурентные записи и предотвращает разветвление цепочки.

### 3.4. Верификация

```bash
# CLI
cd apps/api
uv run python -m scripts.verify_audit_chain
# → "CHAIN OK" или "CHAIN BROKEN: hash mismatch at seq=N"
```

```python
# Программно
from src.services.audit_service import AuditService, ChainBrokenError

service = AuditService(session)
try:
    await service.verify_chain()
except ChainBrokenError as exc:
    print(f"Chain broken at seq={exc.seq}")
```

Алгоритм верификации:
1. Пройти все записи по `seq ASC`
2. Для каждой записи проверить `prev_hash == hash` предыдущей
3. Пересчитать `hash` из полей и сравнить с сохранённым
4. При расхождении → `ChainBrokenError`

---

## 4. Типы действий (Actions)

### 4.1. Полный справочник

| Action | Entity | Где пишется | Что означает |
|--------|--------|-------------|--------------|
| `created` | report | `report_service.create_report` | Создан черновик отчёта |
| `created` | user | `audit_service.log_user_created` | Новый пользователь при SSO-login |
| `updated` | report | `report_service.update_report` | Изменён отчёт (данные/ссылки) |
| `updated` | user | `audit_service.log_user_profile_updated` | Обновлён профиль (email/name из SSO) |
| `updated` | rule | `criteria_service.update_rule` | Изменена конфигурация правила |
| `status_changed` | report | `report_service.submit_report` | DRAFT → ON_MODERATION |
| `status_changed` | report | `moderation_service.moderate_report` | Approve / Changes Required / Close |
| `status_changed` | report | `moderation_service.dispute_report` | APPROVED → DISPUTED |
| `status_changed` | report | `moderation_service.complete_report` | APPROVED → COMPLETED |
| `status_changed` | report | `archive_service.archive_period` | COMPLETED/CLOSED → ARCHIVED |
| `status_changed` | report | `archive_service.complete_approved_if_stale` | APPROVED → COMPLETED (auto-timer) |
| `points_updated` | report | `moderation_service.moderate_report` | Модератор изменил `finalPoints` |
| `calculation_updated` | report | `report_service.set_calculation` | Смена `calculation_method` / `manualPoints` |
| `deleted` | report | `report_service.soft_delete_report` | Soft-delete черновика |
| `comment` | report | `comments_service.add_report_comment` | Обычный комментарий |
| `sudo_action` | report | `audit_service.log_sudo_action` | Sudo: force_status / restore / override |

### 4.2. Структура `old_value` / `new_value`

#### `created` (report)
```json
{
  "old_value": null,
  "new_value": {
    "status": "DRAFT",
    "club_id": "uuid",
    "criteria_id": "uuid",
    "calculated_points": 500,
    "is_overdue": false
  }
}
```

#### `updated` (report)
```json
{
  "old_value": {
    "activity_date": "2026-09-15T12:00:00+00:00",
    "report_data": {"count": 1},
    "calculated_points": 250,
    "links": ["https://t.me/club/1"]
  },
  "new_value": {
    "activity_date": "2026-09-15T12:00:00+00:00",
    "report_data": {"count": 3},
    "calculated_points": 500
  }
}
```

#### `status_changed` (moderation)
```json
{
  "old_value": {
    "status": "ON_MODERATION",
    "final_points": null,
    "moderation_comment": null
  },
  "new_value": {
    "status": "APPROVED",
    "final_points": 500,
    "moderation_comment": "Looks good"
  }
}
```

#### `points_updated`
```json
{
  "old_value": {"calculated_points": 500},
  "new_value": {"final_points": 200}
}
```

#### `calculation_updated`
```json
{
  "old_value": {
    "calculation_method": "auto",
    "manual_points": null
  },
  "new_value": {
    "calculation_method": "manual",
    "manual_points": 350
  }
}
```

#### `comment`
```json
{
  "old_value": null,
  "new_value": {"body": "Текст комментария"}
}
```

#### `sudo_action`
```json
{
  "old_value": {"status": "DRAFT"},
  "new_value": {
    "status": "COMPLETED",
    "sudo_action": "force_status"
  },
  "reason": "cleanup after test"
}
```

#### `created` / `updated` (user)
```json
{
  "old_value": null,
  "new_value": {
    "id": "uuid",
    "sso_id": "sso-mod-1",
    "email": "moderator@innopolis.university",
    "name": "Тимофей Модератор",
    "role": "MODERATOR",
    "can_sudo": true
  }
}
```

#### `updated` (rule)
```json
{
  "old_value": {
    "rule_type": "tiered",
    "config": {"tiers": [{"count": 1, "pts": 250}]},
    "priority": 0
  },
  "new_value": {
    "rule_type": "tiered",
    "config": {"tiers": [{"count": 1, "pts": 300}]},
    "priority": 0
  }
}
```

### 4.3. Типы сущностей (`entity_type`)

| Entity type | Описание |
|-------------|----------|
| `report` | Отчёт о деятельности клуба |
| `user` | Пользователь системы |
| `rule` | Правило расчёта баллов (`criteria_rules`) |

---

## 5. Защита от модификации

### 5.1. Триггер БД

```sql
CREATE OR REPLACE FUNCTION prevent_audit_logs_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs is append-only (attempted %)', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_logs_append_only
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION prevent_audit_logs_mutation();
```

**Результат:** любая попытка `UPDATE` или `DELETE` на `audit_logs` завершается ошибкой, даже от владельца таблицы.

### 5.2. REVOKE

```sql
REVOKE UPDATE, DELETE ON audit_logs FROM PUBLIC;
```

### 5.3. Advisory Lock

Перед записью берётся `pg_advisory_xact_lock`, что предотвращает race condition при конкурентных записях (два запроса не смогут получить одинаковый `prev_hash`).

### 5.4. FK RESTRICT

`performed_by_id` имеет `ondelete=RESTRICT` — нельзя удалить пользователя, на которого ссылаются записи аудита.

---

## 6. API

### 6.1. GET /api/admin/audit — Список записей аудита

**Требуется:** роль `MODERATOR`

**Параметры запроса:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `entityType` | string | — | Фильтр по типу сущности |
| `entityId` | string | — | Фильтр по ID сущности |
| `limit` | int (1–200) | 50 | Количество записей |
| `offset` | int ≥0 | 0 | Смещение |

**Ответ:**
```json
{
  "data": {
    "items": [
      {
        "id": "uuid",
        "seq": 29,
        "entityType": "report",
        "entityId": "uuid",
        "action": "status_changed",
        "oldValue": {"status": "ON_MODERATION"},
        "newValue": {"status": "APPROVED", "final_points": 500},
        "performedByName": "Тимофей Модератор",
        "performedByRole": "MODERATOR",
        "performedAt": "2026-09-17T22:00:00+00:00",
        "reason": null,
        "hash": "abc123..."
      }
    ],
    "total": 29,
    "limit": 50,
    "offset": 0
  }
}
```

**Пример:**
```bash
curl "http://127.0.0.1:8000/api/admin/audit?entityType=report&entityId=uuid&limit=10" \
  -H "Authorization: Bearer $MOD_TOKEN"
```

### 6.2. GET /api/reports/:id/comments — Тред комментариев

**Требуется:** любой авторизованный пользователь (leader/moderator)

Возвращает записи аудита, связанные с отчётом, в виде треда (GitHub Issues style).

**Ответ:**
```json
{
  "data": [
    {
      "id": "uuid",
      "action": "created",
      "authorName": "Лидер Клуба",
      "authorRole": "CLUB_LEADER",
      "body": "status → DRAFT",
      "oldValue": null,
      "newValue": {"status": "DRAFT", ...},
      "createdAt": "2026-09-17T20:00:00+00:00"
    },
    {
      "id": "uuid",
      "action": "comment",
      "authorName": "Тимофей Модератор",
      "authorRole": "MODERATOR",
      "body": "Looks good",
      "oldValue": null,
      "newValue": {"body": "Looks good"},
      "createdAt": "2026-09-17T22:00:00+00:00"
    }
  ]
}
```

**Как формируется `body`:**

| Action | Источник body |
|--------|---------------|
| `comment` | `new_value.body` |
| `status_changed` | `reason` или `new_value.moderation_comment` или `status → {status}` |
| `points_updated` | `final_points → {value}` |
| `calculation_updated` | `calculation → {method} ({pts} pts)` |
| `created` / `updated` | `status → {status}` или `action` |

### 6.3. POST /api/reports/:id/comments — Добавить комментарий

**Требуется:** leader или moderator, отчёт не ARCHIVED

**Запрос:**
```json
{"body": "Текст комментария"}
```

**Ответ (201):**
```json
{
  "data": {
    "id": "uuid",
    "action": "comment",
    "authorName": "Лидер Клуба",
    "authorRole": "CLUB_LEADER",
    "body": "Текст комментария",
    "oldValue": null,
    "newValue": {"body": "Текст комментария"},
    "createdAt": "2026-09-17T22:00:00+00:00"
  }
}
```

---

## 7. AuditService — API для разработчиков

### 7.1. Базовое логирование

```python
from src.services.audit_service import AuditService

audit = AuditService(session)
await audit.log(
    entity_type="report",
    entity_id=report.id,
    action="status_changed",
    performed_by_id=user.id,
    performed_by_role=user.role.value,
    old_value={"status": "DRAFT"},
    new_value={"status": "ON_MODERATION"},
    reason="submitted by leader",
)
```

### 7.2. Специализированные методы

```python
# Создание пользователя
await audit.log_user_created(user)

# Обновление профиля
await audit.log_user_profile_updated(user, old_snapshot=old_data)

# Sudo-действие (двойной лог: sudo_actions + audit_logs)
sudo_row, audit_row = await audit.log_sudo_action(
    performed_by=moderator,
    action="force_status",
    entity_type="report",
    entity_id=report.id,
    old_value={"status": "DRAFT"},
    new_value={"status": "COMPLETED"},
    reason="cleanup after test",
)
```

### 7.3. Верификация цепочки

```python
# Бросает ChainBrokenError при нарушении
await audit.verify_chain()

# Или возвращает bool
is_valid = await audit.is_chain_valid()
```

---

## 8. Тред комментариев (GitHub Issues Style)

Система комментариев реализована **без отдельной таблицы** — все записи извлекаются из `audit_logs`.

### 8.1. Как это работает

1. Каждое действие пишется в `audit_logs`
2. `GET /api/reports/:id/comments` выбирает записи с `entity_type="report"` и `entity_id=report_id`
3. Фильтр по `_COMMENT_ACTIONS`:
   ```python
   _COMMENT_ACTIONS = [
       "created",
       "updated",
       "status_changed",
       "points_updated",
       "deleted",
       "sudo_action",
       "comment",
       "calculation_updated",
   ]
   ```
4. Для каждой записи формируется `body` из `reason` / `new_value`
5. Результат сортируется по `seq ASC`

### 8.2. Преимущества

- Нет дублирования данных
- Полная история в одном месте
- Hash chain защищает и комментарии тоже
- Гибкость: можно менять логику отображения без миграций

---

## 9. Sudo Actions

### 9.1. Двойное логирование

Каждое sudo-действие пишется **два раза**:
1. В `sudo_actions` — отдельная таблица для быстрого поиска
2. В `audit_logs` с `action="sudo_action"` — для общей истории

### 9.2. Типы sudo-действий

| Action | Что делает |
|--------|------------|
| `force_status` | Принудительная смена статуса (мимо state machine) |
| `restore_deleted` | Восстановление soft-deleted отчёта |
| `override_points` | Принудительная установка `finalPoints` |

### 9.3. Валидация

- `reason` — **обязателен**, не может быть пустым
- Пользователь должен иметь `role=MODERATOR` и `can_sudo=true`
- При нарушении → `ValueError` или `PermissionError`

---

## 10. Access Violations

### 10.1. Когда пишется

При любом HTTP 403 (Forbidden) автоматически создаётся запись в `access_violations`.

### 10.2. Что логируется

- `user_id` — из JWT (null для анонимных)
- `path` — URL запроса
- `method` — HTTP метод
- `detail` — сообщение об ошибке + IP клиента

### 10.3. Пример записи

```json
{
  "user_id": null,
  "path": "/api/reports",
  "method": "POST",
  "detail": "192.168.1.1: Moderator role required",
  "occurred_at": "2026-09-17T22:00:00+00:00"
}
```

---

## 11. Тестирование

### 11.1. Unit-тесты

```bash
cd apps/api
uv run pytest tests/test_audit_hash.py -v
```

Покрывают:
- Genesis hash = 64 нуля
- Детерминированность `compute_hash`
- Изменение хеша при изменении payload

### 11.2. Integration-тесты

```bash
uv run pytest tests/test_audit_chain_db.py -v
```

Покрывают:
- Построение цепочки и верификация
- Триггер блокирует UPDATE
- Триггер блокирует DELETE
- Sudo пишет в обе таблицы
- Обнаружение tamper (INSERT с неверным `prev_hash`)

### 11.3. E2E-тесты

```bash
uv run pytest tests/test_e2e.py tests/test_e2e_extended.py -v
```

Покрывают:
- Полный lifecycle отчёта с аудитом
- Comments thread
- Audit list с фильтрами

---

## 12. Операции

### 12.1. Верификация цепочки

```bash
cd apps/api
uv run python -m scripts.verify_audit_chain
```

### 12.2. Просмотр аудита через API

```bash
# Все записи
curl "http://127.0.0.1:8000/api/admin/audit" -H "Authorization: Bearer $MOD_TOKEN"

# По отчёту
curl "http://127.0.0.1:8000/api/admin/audit?entityType=report&entityId=uuid" \
  -H "Authorization: Bearer $MOD_TOKEN"
```

### 12.3. Просмотр через SQL

```sql
-- Последние 10 записей
SELECT seq, entity_type, entity_id, action, performed_by_role, performed_at
FROM audit_logs
ORDER BY seq DESC
LIMIT 10;

-- История отчёта
SELECT seq, action, old_value, new_value, reason, performed_at
FROM audit_logs
WHERE entity_type = 'report' AND entity_id = 'uuid'
ORDER BY seq ASC;

-- Проверка цепочки (первые 5)
SELECT seq, prev_hash, hash
FROM audit_logs
ORDER BY seq ASC
LIMIT 5;
```

### 12.4. Troubleshooting

**Проблема:** `ChainBrokenError` при верификации

**Причины:**
1. Записи были вставлены напрямую в БД (мимо `AuditService`)
2. Была нарушена целостность БД
3. Конкурентная запись без advisory lock (не должно случиться)

**Решение:**
```bash
# Найти сломанное место
uv run python -m scripts.verify_audit_chain
# → "CHAIN BROKEN: hash mismatch at seq=42"

# Посмотреть запись
SELECT * FROM audit_logs WHERE seq = 42;

# Сравнить с предыдущей
SELECT * FROM audit_logs WHERE seq = 41;
```

---

## 13. Расширение

### 13.1. Добавление нового action

1. Написать запись через `AuditService.log()` с новым `action`
2. Добавить action в `_COMMENT_ACTIONS` если нужно в треде
3. Обновить `_build_body()` в `comments_service.py` для отображения
4. Обновить эту документацию

### 13.2. Добавление нового entity_type

1. Использовать новый `entity_type` в `AuditService.log()`
2. Добавить фильтр в `GET /api/admin/audit` (уже поддерживается)
3. Обновить документацию

### 13.3. Кастомные поля в new_value

`new_value` — JSONB, можно добавлять любые поля:
```python
await audit.log(
    entity_type="report",
    entity_id=report.id,
    action="custom_action",
    performed_by_id=user.id,
    performed_by_role=user.role.value,
    new_value={
        "custom_field": "value",
        "metadata": {"source": "api"},
    },
)
```

---

## 14. Ссылки

| Документ | Путь |
|----------|------|
| Архитектура | `/docs/04_ARCHITECTURE.md` |
| API Contract | `/docs/shared/api-contract.ts` |
| Schema | `/docs/shared/schema.prisma` |
| AuditService | `/apps/api/src/services/audit_service.py` |
| Comments Service | `/apps/api/src/services/comments_service.py` |
| Verify Script | `/apps/api/scripts/verify_audit_chain.py` |
| Tests | `/apps/api/tests/test_audit_*.py` |
