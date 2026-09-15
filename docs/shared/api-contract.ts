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
  links: { url: string; domain: string }[];
}

export interface ApiSuccess<T> { data: T }
export interface ApiError { error: { code: string; message: string } }

// === Endpoints (Основные) ===
// POST   /api/reports                  -> CreateReportDTO -> ReportResponse
// PATCH  /api/reports/:id              -> (Лидер обновляет черновик)
// PATCH  /api/reports/:id/moderate     -> ModerateReportDTO -> ReportResponse (Только модератор)
// POST   /api/reports/:id/dispute      -> { comment: string } -> ReportResponse (Лидер оспаривает APPROVED)
// GET    /api/rating?semester=2026-fall -> { clubs: { id, name, totalPoints, breakdown }[] }
// POST   /api/admin/sync/force         -> { semester: string } -> { status: 'queued' } (Только модератор)
// POST   /api/admin/sudo               -> SudoActionDTO -> { success: true } (Только модератор с can_sudo)

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
 */
