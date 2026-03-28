import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

import { api } from '../api/client'
import type { AuthResponse, AuthUser } from '../api/types'

type AuthContextValue = {
  user: AuthUser | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, inviteCode: string, name?: string) => Promise<void>
  bootstrap: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

type StoredSession = {
  token: string
  user: AuthUser
}

const SESSION_KEY = 'oahuai-seed-session'
const AuthContext = createContext<AuthContextValue | null>(null)

function parseStoredSession(): StoredSession | null {
  const raw = window.localStorage.getItem(SESSION_KEY)

  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw) as StoredSession
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const clearSession = () => {
    setUser(null)
    setToken(null)
    api.setAuthToken(null)
    window.localStorage.removeItem(SESSION_KEY)
  }

  const persistSession = (response: AuthResponse) => {
    setUser(response.user)
    setToken(response.access_token)
    api.setAuthToken(response.access_token)
    window.localStorage.setItem(
      SESSION_KEY,
      JSON.stringify({
        token: response.access_token,
        user: response.user,
      }),
    )
  }

  useEffect(() => {
    const restore = async () => {
      const session = parseStoredSession()

      if (!session) {
        setIsLoading(false)
        return
      }

      api.setAuthToken(session.token)

      try {
        const restoredUser = await api.getMe()
        setUser(restoredUser)
        setToken(session.token)
        window.localStorage.setItem(
          SESSION_KEY,
          JSON.stringify({
            token: session.token,
            user: restoredUser,
          }),
        )
      } catch {
        clearSession()
      } finally {
        setIsLoading(false)
      }
    }

    api.onAuthError(() => {
      clearSession()
    })

    void restore()

    return () => {
      api.onAuthError(null)
    }
  }, [])

  const login = async (email: string, password: string) => {
    persistSession(await api.login(email, password))
  }

  const register = async (email: string, password: string, inviteCode: string, name?: string) => {
    persistSession(await api.register(email, password, inviteCode, name))
  }

  const bootstrap = async (email: string, password: string) => {
    persistSession(await api.bootstrap(email, password))
  }

  const logout = async () => {
    clearSession()
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        register,
        bootstrap,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }

  return context
}
