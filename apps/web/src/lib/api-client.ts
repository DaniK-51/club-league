import type {
  ApiSuccess,
  CommentEntry,
  CreateReportDTO,
  CriteriaOut,
  LoginResponse,
  MeResponse,
  ModerateReportDTO,
  RatingResponse,
  ReportResponse,
  SudoActionDTO,
} from './types'
import { ApiError } from './types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

type TokenListener = (accessToken: string | null) => void

class ApiClient {
  private accessToken: string | null = null
  private refreshToken: string | null = null
  private refreshPromise: Promise<boolean> | null = null
  private onTokenChange: TokenListener | null = null

  setTokens(access: string | null, refresh: string | null) {
    this.accessToken = access
    this.refreshToken = refresh
    this.onTokenChange?.(access)
  }

  setOnTokenChange(listener: TokenListener) {
    this.onTokenChange = listener
  }

  private async tryRefresh(): Promise<boolean> {
    if (!this.refreshToken) return false
    if (this.refreshPromise) return this.refreshPromise

    this.refreshPromise = (async () => {
      try {
        const res = await fetch(`${BASE_URL}/api/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refreshToken: this.refreshToken }),
        })
        if (!res.ok) return false
        const json = (await res.json()) as ApiSuccess<LoginResponse>
        this.setTokens(json.data.accessToken, json.data.refreshToken)
        return true
      } catch {
        return false
      } finally {
        this.refreshPromise = null
      }
    })()

    return this.refreshPromise
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
    retryOn401 = true
  ): Promise<T> {
    const headers: Record<string, string> = {
      ...((options.headers as Record<string, string>) ?? {}),
    }
    if (options.body !== undefined) {
      headers['Content-Type'] = 'application/json'
    }
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`
    }

    const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
    const json = await res.json().catch(() => null)

    if (res.status === 401 && retryOn401) {
      const refreshed = await this.tryRefresh()
      if (refreshed) {
        return this.request<T>(path, options, false)
      }
      this.setTokens(null, null)
    }

    if (!res.ok) {
      const err = json as { error?: { code?: string; message?: string } } | null
      throw new ApiError(
        err?.error?.code ?? 'INTERNAL_SERVER_ERROR',
        err?.error?.message ?? `HTTP ${res.status}`,
        res.status
      )
    }

    return (json as ApiSuccess<T>).data
  }

  // === Auth ===

  async ssoCallback(code: string): Promise<LoginResponse> {
    return this.request<LoginResponse>('/api/auth/sso/callback', {
      method: 'POST',
      body: JSON.stringify({ code }),
    })
  }

  async getMe(): Promise<MeResponse> {
    return this.request<MeResponse>('/api/users/me')
  }

  // === Criteria ===

  async getCriteria(semester?: string, category?: string): Promise<CriteriaOut[]> {
    const params = new URLSearchParams()
    if (semester) params.set('semester', semester)
    if (category) params.set('category', category)
    const qs = params.toString()
    return this.request<CriteriaOut[]>(`/api/criteria${qs ? `?${qs}` : ''}`)
  }

  // === Reports ===

  async createReport(dto: CreateReportDTO): Promise<ReportResponse> {
    return this.request<ReportResponse>('/api/reports', {
      method: 'POST',
      body: JSON.stringify(dto),
    })
  }

  async getReports(): Promise<ReportResponse[]> {
    return this.request<ReportResponse[]>('/api/reports')
  }

  async getReport(id: string): Promise<ReportResponse> {
    return this.request<ReportResponse>(`/api/reports/${id}`)
  }

  async updateReport(
    id: string,
    dto: Partial<CreateReportDTO>
  ): Promise<ReportResponse> {
    return this.request<ReportResponse>(`/api/reports/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(dto),
    })
  }

  async submitReport(id: string): Promise<ReportResponse> {
    return this.request<ReportResponse>(`/api/reports/${id}/submit`, {
      method: 'POST',
    })
  }

  async deleteReport(id: string): Promise<void> {
    await this.request<void>(`/api/reports/${id}`, { method: 'DELETE' })
  }

  async getReportComments(id: string): Promise<CommentEntry[]> {
    return this.request<CommentEntry[]>(`/api/reports/${id}/comments`)
  }

  // === Moderation ===

  async moderateReport(
    id: string,
    dto: ModerateReportDTO
  ): Promise<ReportResponse> {
    return this.request<ReportResponse>(`/api/reports/${id}/moderate`, {
      method: 'PATCH',
      body: JSON.stringify(dto),
    })
  }

  async disputeReport(id: string, comment: string): Promise<ReportResponse> {
    return this.request<ReportResponse>(`/api/reports/${id}/dispute`, {
      method: 'POST',
      body: JSON.stringify({ comment }),
    })
  }

  async completeReport(id: string): Promise<ReportResponse> {
    return this.request<ReportResponse>(`/api/reports/${id}/complete`, {
      method: 'POST',
    })
  }

  async archiveReports(period: string): Promise<{ archived: number }> {
    return this.request<{ archived: number }>(
      `/api/reports/archive?period=${encodeURIComponent(period)}`,
      { method: 'POST' }
    )
  }

  // === Rating ===

  async getRating(semester?: string): Promise<RatingResponse> {
    const qs = semester ? `?semester=${encodeURIComponent(semester)}` : ''
    return this.request<RatingResponse>(`/api/rating${qs}`)
  }

  // === Admin ===

  async forceSync(semester?: string): Promise<{ status: string }> {
    return this.request<{ status: string }>('/api/admin/sync/force', {
      method: 'POST',
      body: JSON.stringify(semester ? { semester } : {}),
    })
  }

  async getSyncStatus(): Promise<{
    lastSyncAt: string | null
    status: string
  }> {
    return this.request('/api/admin/sync/status')
  }

  async sudo(dto: SudoActionDTO): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('/api/admin/sudo', {
      method: 'POST',
      body: JSON.stringify(dto),
    })
  }
}

export const api = new ApiClient()
