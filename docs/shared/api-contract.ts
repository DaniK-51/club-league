// === Enums ===
export type ReportStatus = 'DRAFT' | 'ON_MODERATION' | 'CHANGES_REQUIRED' | 'APPROVED' | 'DISPUTED' | 'COMPLETED' | 'CLOSED' | 'ARCHIVED';

// === DTOs ===
export interface CreateReportDTO {
  criteriaId: string;
  activityDate: string; // ISO 8601
  reportData: Record<string, any>; // Валидируется на бэке по схеме критерия
  links: string[]; // Массив URL
}

export interface ModerateReportDTO {
  status: 'APPROVED' | 'CHANGES_REQUIRED' | 'CLOSED';
  finalPoints?: number; // Если модератор меняет баллы
  comment: string; // Обязателен при CHANGES_REQUIRED или изменении баллов
}

export interface SudoActionDTO {
  action: 'force_status' | 'restore_deleted' | 'override_points';
  targetReportId: string;
  newValue: any;
  reason: string; // Обязательно
}

// === Responses ===
export interface ReportResponse {
  id: string;
  clubName: string;
  criteriaCode: string;
  activityDate: string;
  isOverdue: boolean; // Вычисляется на бэке: activityDate + 7 days < today
  status: ReportStatus;
  calculatedPoints: number | null;
  finalPoints: number | null;
  calculationMethod: 'auto' | 'manual'; // NEW
  manualPoints: number | null;           // NEW
  links: { url: string; domain: string }[];
  reportData: Record<string, unknown>;   // NEW
}

export interface CommentEntry {
  id: string;
  action: string; // "created" | "updated" | "status_changed" | "points_updated" | "deleted" | "sudo_action" | "comment" | "calculation_updated"
  authorName: string;
  authorRole: string;
  body: string;
  oldValue: Record<string, unknown> | null;
  newValue: Record<string, unknown> | null;
  displayData: Record<string, unknown> | null; // NEW — structured data for rendering
  createdAt: string;
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
// POST   /api/reports/:id/comments     -> { body: string } -> CommentEntry (leader/moderator)
// POST   /api/reports/archive?period=  -> batch COMPLETED/CLOSED → ARCHIVED (модератор)
// GET    /api/rating?semester=2026-fall -> { clubs: { id, name, totalPoints, breakdown }[] }
// POST   /api/admin/sync/force         -> { semester?: string } -> { status: 'queued' } (Только модератор)
// GET    /api/admin/sync/status        -> SyncStatus
// POST   /api/admin/sudo               -> SudoActionDTO -> { success: true } (Только модератор с can_sudo)
// GET    /api/admin/rules/:id          -> RuleOut (модератор)
// PATCH  /api/admin/rules/:id          -> UpdateRuleDTO -> RuleOut (модератор; config валидируется)
// GET    /api/admin/audit?entityType=&entityId=&limit=&offset= -> AuditListResponse (модератор)

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
  COMMENT_REQUIRED = 'COMMENT_REQUIRED', // Требуется для CHANGES_REQUIRED или изменения баллов
  RULES_VERSION_NOT_FOUND = 'RULES_VERSION_NOT_FOUND',
  
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
 * - Все события содержат criteriaCode, criteriaName, activityDate.
 * - created: { title, summary, criteriaCode, criteriaName, criteriaNameEn, activityDate,
 *              reportData, links, calculatedPoints, isOverdue }
 * - status_changed: { title, summary, criteriaCode, ..., oldStatus, newStatus,
 *                     calculatedPoints, finalPoints, calculationMethod, manualPoints, moderationComment }
 * - points_updated: { title, summary, criteriaCode, ..., oldPoints, newPoints,
 *                     calculationMethod, manualPoints, moderationComment }
 * - calculation_updated: { title, summary, criteriaCode, ..., oldMethod, newMethod,
 *                          manualPoints, reason }
 * - updated: { title, summary, criteriaCode, ..., changes[], oldCalculatedPoints, newCalculatedPoints }
 * - deleted: { title, summary, criteriaCode, ..., reportData, activityDate }
 * - sudo_action: { title, summary, criteriaCode, ..., sudoAction, targetReportId,
 *                  oldValue, newValue, reason }
 * - archive: { title, summary, criteriaCode, ..., period, batchId }
 * - CommentEntry.displayData отдаёт это поле напрямую.
 */
