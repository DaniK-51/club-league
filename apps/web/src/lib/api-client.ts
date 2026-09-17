// Types re-exported from docs/shared/api-contract.ts
export type ReportStatus =
  | 'DRAFT'
  | 'ON_MODERATION'
  | 'CHANGES_REQUIRED'
  | 'APPROVED'
  | 'DISPUTED'
  | 'COMPLETED'
  | 'CLOSED'
  | 'ARCHIVED'

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

export interface ReportResponse {
  id: string
  clubName: string
  criteriaCode: string
  activityDate: string
  isOverdue: boolean
  status: ReportStatus
  calculatedPoints: number | null
  finalPoints: number | null
  links: { url: string; domain: string }[]
}

export interface MeResponse {
  id: string
  email: string
  name: string
  role: 'CLUB_LEADER' | 'MODERATOR' | 'GUEST'
  canSudo: boolean
  clubIds: string[]
}

export interface LoginResponse {
  accessToken: string
  refreshToken: string
  user: MeResponse
}

export interface ApiSuccess<T> {
  data: T
}

export interface ApiError {
  error: {
    code: string
    message: string
  }
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

class ApiClient {
  private accessToken: string | null = null

  setToken(token: string | null) {
    this.accessToken = token
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<ApiSuccess<T>> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) ?? {}),
    }

    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`
    }

    const res = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers,
    })

    const json = await res.json()

    if (!res.ok) {
      const err = json as ApiError
      throw new Error(err.error?.message || 'API error')
    }

    return json as ApiSuccess<T>
  }

  get<T>(path: string) {
    return this.request<T>(path)
  }

  post<T>(path: string, body?: unknown) {
    return this.request<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  patch<T>(path: string, body?: unknown) {
    return this.request<T>(path, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  delete<T>(path: string) {
    return this.request<T>(path, { method: 'DELETE' })
  }
}

export const api = new ApiClient()
