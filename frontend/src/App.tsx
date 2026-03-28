import { Link, Outlet } from 'react-router-dom'
import { useEffect, useState } from 'react'

import { api, ApiError } from './api/client'
import type { RunResponse } from './api/types'
import { useAuth } from './auth/AuthContext'
import { RunSidebar } from './components/RunSidebar'

export type AppOutletContext = {
  runs: RunResponse[]
  runsLoading: boolean
  runsError: string | null
  refreshRuns: () => Promise<void>
}

export default function App() {
  const { user, logout } = useAuth()
  const [runs, setRuns] = useState<RunResponse[]>([])
  const [runsLoading, setRunsLoading] = useState(true)
  const [runsError, setRunsError] = useState<string | null>(null)

  const refreshRuns = async () => {
    setRunsLoading(true)
    setRunsError(null)
    try {
      const response = await api.listRuns()
      setRuns(response.runs)
    } catch (error) {
      if (error instanceof ApiError) {
        setRunsError(error.message)
        return
      }
      setRunsError('Unable to load workshop projects right now.')
    } finally {
      setRunsLoading(false)
    }
  }

  const outletContext: AppOutletContext = {
    runs,
    runsLoading,
    runsError,
    refreshRuns,
  }

  useEffect(() => {
    void refreshRuns()
  }, [])

  return (
    <div className="app-shell">
      <div className="app-backdrop" />
      <RunSidebar runs={runs} loading={runsLoading} onRefresh={refreshRuns} />
      <div className="app-main">
        <header className="topbar">
          <div>
            <p className="eyebrow">Claude Code / Codex 101</p>
            <h1 className="topbar-title"><Link to="/studio" className="brand-link">OahuAI Seed</Link></h1>
          </div>
          <div className="topbar-actions">
            <div className="operator-chip">
              <span className="operator-name">{user?.name || user?.email}</span>
              <span className="operator-role">{user?.is_admin ? 'admin operator' : 'student operator'}</span>
            </div>
            <button className="button button-ghost" type="button" onClick={() => void logout()}>
              Sign out
            </button>
          </div>
        </header>

        {runsError ? (
          <div className="banner banner-error">{runsError}</div>
        ) : null}

        <main className="app-content">
          <Outlet context={outletContext} />
        </main>
      </div>
    </div>
  )
}
