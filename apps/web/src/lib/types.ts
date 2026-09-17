// Types from docs/shared/api-contract.ts

export type ReportStatus =
  | 'DRAFT'
  | 'ON_MODERATION'
  | 'CHANGES_REQUIRED'
  | 'APPROVED'
  | 'DISPUTED'
  | 'COMPLETED'
  | 'CLOSED'
  | 'ARCHIVED'

export type UserRole = 'GUEST' | 'CLUB_LEADER' | 'MODERATOR'

export type ClubCategory = 'SPORT' | 'TECH' | 'ART' | 'SPECIAL_INTEREST'

// === DTOs ===

export interface CreateReportDTO {
  criteriaId: string
  activityDate: string
  reportData: Record<string, unknown>
  links: string[]
}

export interface ModerateReportDTO {
  status: 'APPROVED' | 'CHANGES_REQUIRED' | 'CLOSED'
  finalPoints?: number
  comment: string
}

export interface SudoActionDTO {
  action: 'force_status' | 'restore_deleted' | 'override_points'
  targetReportId: string
  newValue: unknown
  reason: string
}

// === Responses ===

export interface ReportLink {
  url: string
  domain: string
}

export interface ReportResponse {
  id: string
  clubName: string
  criteriaCode: string
  activityDate: string
  isOverdue: boolean
  status: ReportStatus
  calculatedPoints: number | null
  finalPoints: number | null
  links: ReportLink[]
}

export interface MeResponse {
  id: string
  email: string
  name: string
  role: UserRole
  canSudo: boolean
  clubIds: string[]
}

export interface LoginResponse {
  accessToken: string
  refreshToken: string
  user: MeResponse
}

export interface CriteriaRuleOut {
  id: string
  ruleType: string
  config: Record<string, unknown>
  priority: number
  versionId: string
  semester: string
}

export interface CriteriaOut {
  id: string
  code: string
  nameRu: string
  nameEn: string
  category: ClubCategory | null
  rules: CriteriaRuleOut[]
}

export interface RuleOut {
  id: string
  criteriaId: string
  criteriaCode: string
  ruleType: string
  config: Record<string, unknown>
  priority: number
  versionId: string
  semester: string
}

export interface RatingClub {
  id: string
  name: string
  totalPoints: number
  breakdown: Record<string, number>
}

export interface RatingResponse {
  clubs: RatingClub[]
}

export interface CommentEntry {
  id: string
  action: string
  authorName: string
  authorRole: string
  body: string
  oldValue: Record<string, unknown> | null
  newValue: Record<string, unknown> | null
  createdAt: string
}

// === Admin ===

export interface AuditLogOut {
  id: string
  seq: number
  entityType: string
  entityId: string
  action: string
  oldValue: Record<string, unknown> | null
  newValue: Record<string, unknown> | null
  performedByName: string
  performedByRole: string
  performedAt: string
  reason: string | null
  hash: string
}

export interface AuditListResponse {
  items: AuditLogOut[]
  total: number
  limit: number
  offset: number
}

export interface SyncStatus {
  pending: boolean
  lastRunAt: string | null
  lastError: string | null
  runCount: number
  debounceSeconds: number
}

export interface UpdateRuleDTO {
  config?: Record<string, unknown>
  priority?: number
  ruleType?: string
}

// === API envelope ===

export interface ApiSuccess<T> {
  data: T
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
  }
}

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number
  ) {
    super(message)
    this.name = 'ApiError'
  }
}
