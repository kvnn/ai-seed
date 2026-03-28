import { useLocation, useNavigate } from 'react-router-dom'

import type { RunResponse } from '../api/types'
import { formatDateTime, summarizeBrief } from '../utils/time'

type RunSidebarProps = {
  runs: RunResponse[]
  loading: boolean
  onRefresh: () => Promise<void>
}

export function RunSidebar({ runs, loading, onRefresh }: RunSidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <aside className="run-sidebar">
      <div className="run-sidebar-inner">
        <div>
          <p className="eyebrow">Workshop navigator</p>
          <h2 className="run-sidebar-title">Project queue</h2>
          <p className="run-sidebar-copy">
            Review the current runs, jump back into a project, or start the next workshop exercise.
          </p>
        </div>

        <div className="sidebar-actions">
          <button className="button button-primary sidebar-action" type="button" onClick={() => navigate('/studio')}>
            New workshop run
          </button>
          <button className="button button-ghost sidebar-action" type="button" onClick={() => void onRefresh()}>
            Refresh queue
          </button>
        </div>

        <div className="sidebar-list">
          {loading ? <div className="sidebar-empty">Loading projects...</div> : null}

          {!loading && runs.length === 0 ? (
            <div className="sidebar-empty">No runs yet. Create the first project from the main workspace.</div>
          ) : null}

          {!loading
            ? runs.map((run) => {
              const active = location.pathname === `/studio/runs/${run.id}`

              return (
                <button
                  key={run.id}
                  type="button"
                  className={`sidebar-run${active ? ' is-active' : ''}`}
                  onClick={() => navigate(`/studio/runs/${run.id}`)}
                >
                  <div className="sidebar-run-top">
                    <span className={`status-pill status-${run.status}`}>{run.status.replace(/_/g, ' ')}</span>
                    <span className="sidebar-meta">{formatDateTime(run.updated_at)}</span>
                  </div>
                  <h3 className="sidebar-run-title">{summarizeBrief(run.brief, 46)}</h3>
                  <p className="sidebar-run-subtitle">{run.source_url || run.publish_slug}</p>
                </button>
              )
            })
            : null}
        </div>
      </div>
    </aside>
  )
}
