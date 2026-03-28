import type {
  AuthResponse,
  AuthUser,
  BackendRootResponse,
  RunCreateRequest,
  RunListResponse,
  RunResponse,
  RunStage,
} from './types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  payload: unknown

  constructor(message: string, status: number, payload: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

let authToken: string | null = null
let onAuthError: (() => void) | null = null

function errorMessage(payload: any, status: number) {
  if (typeof payload?.detail === 'string') {
    return payload.detail
  }
  if (typeof payload?.message === 'string') {
    return payload.message
  }
  return `request_failed:${status}`
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string> | undefined),
  }

  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  })

  const text = await response.text()
  let payload: unknown = null

  try {
    payload = text ? JSON.parse(text) : null
  } catch {
    payload = text
  }

  if (!response.ok) {
    if (response.status === 401 && onAuthError) {
      onAuthError()
    }
    throw new ApiError(errorMessage(payload, response.status), response.status, payload)
  }

  return payload as T
}

export const api = {
  baseUrl: API_BASE_URL,

  setAuthToken(token: string | null) {
    authToken = token
  },

  onAuthError(callback: (() => void) | null) {
    onAuthError = callback
  },

  login(email: string, password: string) {
    return apiFetch<AuthResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  },

  register(email: string, password: string, inviteCode: string, name?: string) {
    return apiFetch<AuthResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, invite_code: inviteCode, name }),
    })
  },

  bootstrap(email: string, password: string) {
    return apiFetch<AuthResponse>('/api/auth/bootstrap', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  },

  getMe() {
    return apiFetch<AuthUser>('/api/auth/me')
  },

  getBackendRoot() {
    return apiFetch<BackendRootResponse>('/api/system/backend-root')
  },

  listRuns() {
    return apiFetch<RunListResponse>('/api/runs')
  },

  createRun(body: RunCreateRequest) {
    return apiFetch<RunResponse>('/api/runs', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  getRun(runId: string) {
    return apiFetch<RunResponse>(`/api/runs/${encodeURIComponent(runId)}`)
  },

  approveRun(runId: string, notes?: string) {
    return apiFetch<RunResponse>(`/api/runs/${encodeURIComponent(runId)}/approve`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    })
  },

  retryRun(runId: string, stage?: RunStage) {
    return apiFetch<RunResponse>(`/api/runs/${encodeURIComponent(runId)}/retry`, {
      method: 'POST',
      body: JSON.stringify({ stage }),
    })
  },

  publishRun(runId: string) {
    return apiFetch<RunResponse>(`/api/runs/${encodeURIComponent(runId)}/publish`, {
      method: 'POST',
      body: JSON.stringify({}),
    })
  },

  previewUrl(path?: string | null) {
    if (!path) {
      return null
    }
    return `${API_BASE_URL}${path}`
  },
}
