// === Enums ===
export type ReportStatus = 'DRAFT' | 'ON_MODERATION' | 'CHANGES_REQUIRED' | 'APPROVED' | 'DISPUTED' | 'COMPLETED' | 'CLOSED' | 'ARCHIVED';
export type UserRole = 'GUEST' | 'CLUB_LEADER' | 'MODERATOR';
export type CalculationMethod = 'auto' | 'manual';

// === DTOs ===
export interface CreateReportDTO {
  criteriaId: string;
  activityDate: string; // ISO 8601
  reportData: Record<string, unknown>; // Валидируется на бэке по схеме критерия
  links: string[]; // Массив URL
}

export interface UpdateReportDTO {
  activityDate?: string | null;
  reportData?: Record<string, unknown> | null;
  links?: string[] | null;
}

export interface ModerateReportDTO {
  status: 'APPROVED' | 'CHANGES_REQUIRED' | 'CLOSED';
  finalPoints?: number; // Если модератор меняет баллы
  // Backend default: "". Required for CHANGES_REQUIRED.
  // Required for APPROVED/CLOSED only when finalPoints override auto calculatedPoints.
  // NOT required when calculationMethod="manual" (trail lives in PATCH /calculation).
  comment?: string;
}

export interface DisputeReportDTO {
  comment: string;
}

export interface SetCalculationDTO {
  method: CalculationMethod;
  manualPoints?: number | null; // Required if method = "manual"
  reason?: string | null;
}

export interface CreateCommentDTO {
  body: string;
}

export interface SudoActionDTO {
  action: 'force_status' | 'restore_deleted' | 'override_points';
  targetReportId: string;
  newValue: unknown;
  reason: string; // Обязательно
}

export interface UpdateRuleDTO {
  config?: Record<string, unknown> | null;
  priority?: number | null;
  ruleType?: string | null;
}

// === Responses ===
export interface MeResponse {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  canSudo: boolean;
  clubIds: string[];
}

export interface LoginResponse {
  accessToken: string;
  refreshToken: string;
  user: MeResponse;
}

export interface ReportResponse {
  id: string;
  clubName: string;
  criteriaCode: string;
  activityDate: string;
  isOverdue: boolean;
  status: ReportStatus;
  calculatedPoints: number | null;
  finalPoints: number | null;
  calculationMethod: CalculationMethod;
  manualPoints: number | null;
  periodName: string | null;
  links: { url: string; domain: string }[];
  reportData: Record<string, unknown>;
}

export interface CommentEntry {
  id: string;
  action: string; // "created" | "updated" | "status_changed" | "points_updated" | "deleted" | "sudo_action" | "comment" | "calculation_updated"
  authorName: string;
  authorRole: string;
  body: string;
  oldValue: Record<string, unknown> | null;
  newValue: Record<string, unknown> | null;
  displayData: Record<string, unknown> | null; // Structured data for rendering
  createdAt: string;
}

export interface RatingClub {
  id: string;
  name: string;
  totalPoints: number;
  breakdown: Record<string, number>;
}

export interface CriteriaRuleOut {
  id: string;
  ruleType: string;
  config: Record<string, unknown>;
  priority: number;
  versionId: string;
  semester: string;
}

export interface CriteriaOut {
  id: string;
  code: string;
  nameRu: string;
  nameEn: string;
  category: string | null;
  rules: CriteriaRuleOut[];
}

export interface RuleOut {
  id: string;
  criteriaId: string;
  criteriaCode: string;
  ruleType: string;
  config: Record<string, unknown>;
  priority: number;
  versionId: string;
  semester: string;
}

export interface AuditLogOut {
  id: string;
  seq: number;
  entityType: string;
  entityId: string;
  action: string;
  oldValue: Record<string, unknown> | null;
  newValue: Record<string, unknown> | null;
  displayData: Record<string, unknown> | null;
  performedByName: string;
  performedByRole: string;
  performedAt: string;
  reason: string | null;
  hash: string;
}

export interface AuditListResponse {
  items: AuditLogOut[];
  total: number;
  limit: number;
  offset: number;
}

export interface SyncStatus {
  pending: boolean;
  lastRunAt: string | null;
  lastError: string | null;
  runCount: number;
  debounceSeconds: number;
}

export interface SyncQueued {
  status: 'queued';
}

export interface SudoSuccess {
  success: true;
}

export interface PeriodOut {
  id: string;
  name: string;
  startDate: string;
  endDate: string;
  isArchived: boolean;
  reportCount: number;
}

export interface CreatePeriodDTO {
  name: string;
  startDate: string;
  endDate: string;
}

export interface UpdatePeriodDTO {
  name?: string | null;
  startDate?: string | null;
  endDate?: string | null;
}

export interface ArchivePeriodResponse {
  id: string;
  period: string; // Period.name
  reportCount: number;
  archivedAt: string; // ISO datetime
}

export interface ApiSuccess<T> { data: T }
export interface ApiError { error: { code: string; message: string } }

// === Endpoints (Основные) ===
// POST   /api/auth/sso/callback        -> { code } -> { accessToken, refreshToken, user }
// POST   /api/auth/refresh             -> { refreshToken } -> LoginResponse
// GET    /api/users/me                 -> MeResponse
// GET    /api/criteria?semester=&category= -> CriteriaOut[]  (public v2 catalog)
// POST   /api/reports                  -> CreateReportDTO -> ReportResponse
// GET    /api/reports                  -> ReportResponse[]
// GET    /api/reports/:id              -> ReportResponse
// PATCH  /api/reports/:id              -> (Лидер обновляет черновик)
// POST   /api/reports/:id/submit       -> DRAFT/CHANGES_REQUIRED → ON_MODERATION
// DELETE /api/reports/:id              -> soft-delete only DRAFT
// GET    /api/reports/:id/comments     -> CommentEntry[] (from audit_logs)
// PATCH  /api/reports/:id/moderate     -> ModerateReportDTO -> ReportResponse (Только модератор)
// POST   /api/reports/:id/dispute      -> { comment: string } -> ReportResponse (Лидер оспаривает APPROVED)
// POST   /api/reports/:id/complete     -> APPROVED → COMPLETED
// PATCH  /api/reports/:id/calculation  -> SetCalculationDTO -> ReportResponse (модератор, без смены статуса)
// POST   /api/reports/:id/comments     -> CreateCommentDTO -> CommentEntry (leader/moderator)
// POST   /api/reports/archive?period=  -> ArchivePeriodResponse (модератор; Period table only)
// GET    /api/rating?period=&semester=  -> { clubs: RatingClub[] } (period приоритетнее)
// GET    /api/periods                   -> PeriodOut[] (public; active + archived)
// POST   /api/admin/sync/force         -> { semester?: string } -> { status: 'queued' } (Только модератор)
// GET    /api/admin/sync/status        -> SyncStatus
// POST   /api/admin/sudo               -> SudoActionDTO -> { success: true } (Только модератор с can_sudo)
// GET    /api/admin/rules/:id          -> RuleOut (модератор)
// PATCH  /api/admin/rules/:id          -> UpdateRuleDTO -> RuleOut (модератор; config валидируется)
// GET    /api/admin/audit?entityType=&entityId=&limit=&offset= -> AuditListResponse (модератор)
// GET    /api/admin/periods             -> PeriodOut[] (модератор)
// POST   /api/admin/periods             -> CreatePeriodDTO -> PeriodOut (модератор)
// PATCH  /api/admin/periods/:id         -> UpdatePeriodDTO -> PeriodOut (модератор)
// DELETE /api/admin/periods/:id         -> { success: true } (модератор; только без отчётов)

// === Error Codes ===
export enum ErrorCode {
  // Auth & Permissions
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  SUDO_REQUIRED = 'SUDO_REQUIRED',
  NOT_CLUB_LEADER = 'NOT_CLUB_LEADER',
  
  // Validation
  INVALID_URL_FORMAT = 'INVALID_URL_FORMAT',
  DOMAIN_NOT_ALLOWED = 'DOMAIN_NOT_ALLOWED',
  DUPLICATE_LINK = 'DUPLICATE_LINK',
  INVALID_ACTIVITY_DATE = 'INVALID_ACTIVITY_DATE', // Дата в будущем или слишком старая
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  RATE_LIMITED = 'RATE_LIMITED',
  
  // Business Logic
  REPORT_NOT_FOUND = 'REPORT_NOT_FOUND',
  INVALID_STATUS_TRANSITION = 'INVALID_STATUS_TRANSITION',
  COMMENT_REQUIRED = 'COMMENT_REQUIRED',
  RULES_VERSION_NOT_FOUND = 'RULES_VERSION_NOT_FOUND',
  PERIOD_NOT_FOUND = 'PERIOD_NOT_FOUND',
  ALREADY_ARCHIVED = 'ALREADY_ARCHIVED',
  
  // System
  INTERNAL_SERVER_ERROR = 'INTERNAL_SERVER_ERROR',
  YANDEX_SYNC_FAILED = 'YANDEX_SYNC_FAILED',
}

// === Auth Flow Description (для документации) ===
/**
 * AUTH FLOW:
 * 1. User clicks "Login with SSO" on Frontend.
 * 2. Frontend redirects to University SSO Provider (OAuth2/SAML).
 * 3. SSO Provider redirects back to Frontend callback with `code`.
 * 4. Frontend sends `code` to Backend: POST /api/auth/sso/callback
 * 5. Backend validates `code` with SSO Provider, gets user profile (email, name, sso_id).
 * 6. Backend checks DB:
 *    - If user exists: return JWT (access + refresh).
 *    - If user is new: create User with role='GUEST', return JWT.
 * 7. Frontend stores JWT and fetches user profile: GET /api/users/me
 * 8. Backend returns: { role: 'CLUB_LEADER' | 'MODERATOR' | 'GUEST', can_sudo: boolean, club_ids: string[] }
 * 
 * SUDO MODE:
 * - Только для пользователей с role='MODERATOR' и can_sudo=true.
 * - Любое действие с флагом sudo требует обязательного поля `reason` в DTO.
 * - Все sudo-действия логируются в таблицу `sudo_actions` и `audit_logs`.
 *
 * AUDIT DISPLAY_DATA:
 * - Каждая запись audit_logs содержит display_data (JSONB) для фронтенда.
 * - Базовые поля (все события отчёта): title, summary, criteriaCode, criteriaName,
 *   criteriaNameEn, activityDate.
 * - created: + reportData, links[], calculatedPoints, isOverdue
 * - updated: + changes[] (field/old/new), oldCalculatedPoints, newCalculatedPoints
 * - status_changed: + oldStatus, newStatus, calculatedPoints, finalPoints,
 *   calculationMethod, manualPoints, moderationComment
 * - points_updated: + oldPoints, newPoints, calculationMethod, manualPoints, moderationComment
 * - calculation_updated: + oldMethod, newMethod, manualPoints, reason
 * - deleted: + reportData
 * - sudo_action: + sudoAction, targetReportId, oldValue, newValue, reason
 * - archive (status_changed): + period, batchId
 * - CommentEntry.displayData отдаёт это поле напрямую (camelCase).
 * - CommentEntry.body = display_data.summary (fallback: reason / new_value).
 *
 * PERIODS:
 * - Period — сущность в БД (name, startDate, endDate, isArchived).
 * - Report привязывается к Period по activity_date при create/update (start <= date < end).
 * - ReportResponse.periodName — имя периода или null (вне всех периодов).
 * - GET /api/periods — public (no auth): all periods incl. isArchived, for rating filter.
 * - GET /api/admin/periods — moderator only; delete only when reportCount=0.
 * - GET /api/rating?period=<name>:
 *     1) Period table by name
 *     2) else semester_range() fallback ("YYYY-fall|spring|summer")
 *     3) else no date filter (all COMPLETED + ARCHIVED reports)
 *   Without params → last non-archived Period by startDate; if none → current_semester fallback.
 *   Rating statuses: COMPLETED + ARCHIVED (archived period totals stay stable after archive).
 * - POST /api/reports/archive?period=<name>:
 *     Period table ONLY (no semester fallback).
 *     404 PERIOD_NOT_FOUND if missing; 400 ALREADY_ARCHIVED if already archived.
 *     After batch: Period.isArchived = true.
 * - Approve: при calculation_method="manual" comment НЕ обязателен.
 * - Audit entity_type="period": actions created / updated / deleted (moderator CRUD).
 *
 * KNOWN GAPS (documented, not bugs):
 * - POST /api/admin/sync/force accepts { semester } but debounced flush currently
 *   recomputes rating for the current Period (get_current_period), not the forced semester.
 * - C7 frequency limit is approximated as a monthly point cap in rating_caps.
 * - S3 host-win modifier seed uses reportData.host_underdog >= 1
 *   (catalog formula invited_teams < host_teams is the product rulebook; hybrid by design).
 */
