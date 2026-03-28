import { useEffect, useState } from 'react'
import { useOutletContext, useParams } from 'react-router-dom'

import type { AppOutletContext } from '../App'
import { api, ApiError } from '../api/client'
import type { RunResponse, RunStage } from '../api/types'
import { formatDateTime, summarizeBrief } from '../utils/time'

const stageLabels = ['research_ready', 'brand_ready', 'site_ready', 'approved', 'published'] as const

function describeAction(action: string) {
  if (action === 'publish') return 'Publish approved site'
  if (action === 'approve_research') return 'Approve research'
  if (action === 'approve_brand') return 'Approve brand'
  if (action === 'approve_site') return 'Approve site'
  if (action === 'retry_research') return 'Retry research'
  if (action === 'retry_brand') return 'Retry brand'
  if (action === 'retry_site') return 'Retry site'
  return action.replace(/_/g, ' ')
}

function stageFromAction(action: string): RunStage | undefined {
  if (action === 'retry_research') return 'research'
  if (action === 'retry_brand') return 'brand'
  if (action === 'retry_site') return 'site'
  return undefined
}

export default function Workspace() {
  const { runId = '' } = useParams()
  const { refreshRuns } = useOutletContext<AppOutletContext>()
  const [run, setRun] = useState<RunResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [approvalNotes, setApprovalNotes] = useState('')
  const [pendingAction, setPendingAction] = useState<string | null>(null)

  const loadRun = async () => {
    setLoading(true)
    setError(null)

    try {
      setRun(await api.getRun(runId))
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        setError(requestError.message)
      } else {
        setError('Unable to load this workshop run.')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadRun()
  }, [runId])

  const handleAction = async (action: string) => {
    setPendingAction(action)
    setError(null)

    try {
      let updatedRun: RunResponse

      if (action.startsWith('approve_')) {
        updatedRun = await api.approveRun(runId, approvalNotes.trim() || undefined)
      } else if (action.startsWith('retry_')) {
        updatedRun = await api.retryRun(runId, stageFromAction(action))
      } else if (action === 'publish') {
        updatedRun = await api.publishRun(runId)
      } else {
        return
      }

      setRun(updatedRun)
      if (action.startsWith('approve_')) {
        setApprovalNotes('')
      }
      await refreshRuns()
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        setError(requestError.message)
      } else {
        setError('The requested workflow action failed.')
      }
    } finally {
      setPendingAction(null)
    }
  }

  if (loading) {
    return <div className="panel">Loading run workspace...</div>
  }

  if (!run) {
    return <div className="panel">This run could not be found.</div>
  }

  const previewHref = api.previewUrl(run.preview_url)

  return (
    <div className="page-stack">
      <section className="panel panel-hero">
        <div className="panel-header">
          <p className="eyebrow">Run workspace</p>
          <h2 className="hero-title">{summarizeBrief(run.brief, 92)}</h2>
          <p className="hero-body">
            This workspace tracks the workshop run from brief to published site. Review each artifact, approve when it
            is strong enough, and publish only after the generated site looks credible.
          </p>
        </div>
        <div className="workspace-meta">
          <span className={`status-pill status-${run.status}`}>{run.status.replace(/_/g, ' ')}</span>
          <span>Slug: {run.publish_slug}</span>
          <span>Updated: {formatDateTime(run.updated_at)}</span>
          {run.published_at ? <span>Published: {formatDateTime(run.published_at)}</span> : null}
        </div>
      </section>

      {error ? <div className="banner banner-error">{error}</div> : null}

      <section className="panel">
        <div className="panel-header">
          <p className="eyebrow">Progress</p>
          <h3 className="section-title">Approval path</h3>
        </div>
        <div className="stage-track">
          {stageLabels.map((status) => {
            const active = run.status === status
            const complete =
              stageLabels.indexOf(status) <= stageLabels.indexOf(run.status as typeof stageLabels[number]) &&
              run.status !== 'failed'

            return (
              <div key={status} className={`stage-chip${active ? ' is-active' : ''}${complete ? ' is-complete' : ''}`}>
                {status.replace(/_/g, ' ')}
              </div>
            )
          })}
          {run.status === 'failed' ? <div className="stage-chip is-failed">failed: {run.failed_stage || 'unknown'}</div> : null}
        </div>
      </section>

      <section className="workspace-grid">
        <article className="panel">
          <div className="panel-header">
            <p className="eyebrow">Operator actions</p>
            <h3 className="section-title">Advance the run</h3>
          </div>

          <label className="field">
            <span>Approval notes</span>
            <textarea
              value={approvalNotes}
              onChange={(event) => setApprovalNotes(event.target.value)}
              rows={4}
              placeholder="Optional notes recorded alongside the stage approval."
            />
          </label>

          <div className="action-stack">
            {run.next_actions.map((action) => (
              <button
                key={action}
                type="button"
                className={`button ${action === 'publish' ? 'button-accent' : 'button-primary'}`}
                onClick={() => void handleAction(action)}
                disabled={pendingAction !== null}
              >
                {pendingAction === action ? 'Working...' : describeAction(action)}
              </button>
            ))}
          </div>

          {run.last_error ? (
            <div className="callout">
              <strong>Last error:</strong> {run.last_error}
            </div>
          ) : null}

          {run.published_path ? (
            <div className="callout">
              <strong>Published path:</strong> {run.published_path}
            </div>
          ) : null}
        </article>

        <article className="panel">
          <div className="panel-header">
            <p className="eyebrow">Site preview</p>
            <h3 className="section-title">Generated website</h3>
          </div>

          {previewHref ? (
            <>
              <a className="preview-link" href={previewHref} target="_blank" rel="noreferrer">
                Open preview in a new tab
              </a>
              <iframe title="Workshop run preview" src={previewHref} className="preview-frame" />
            </>
          ) : (
            <div className="empty-state">Approve the brand stage to generate the site preview.</div>
          )}
        </article>
      </section>

      <section className="workspace-grid">
        <article className="panel">
          <div className="panel-header">
            <p className="eyebrow">Research</p>
            <h3 className="section-title">Scope and constraints</h3>
          </div>
          {run.research ? (
            <div className="artifact-stack">
              <p>{run.research.summary}</p>
              <div className="detail-block">
                <span className="detail-label">Audience</span>
                <p>{run.research.recommended_audience}</p>
              </div>
              <div className="detail-block">
                <span className="detail-label">Key facts</span>
                <ul>
                  {run.research.key_facts.map((fact) => <li key={fact}>{fact}</li>)}
                </ul>
              </div>
              <div className="detail-block">
                <span className="detail-label">Cautions</span>
                <ul>
                  {run.research.cautions.map((caution) => <li key={caution}>{caution}</li>)}
                </ul>
              </div>
            </div>
          ) : (
            <div className="empty-state">Research artifact has not been generated yet.</div>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <p className="eyebrow">Brand</p>
            <h3 className="section-title">Voice and visual direction</h3>
          </div>
          {run.brand ? (
            <div className="artifact-stack">
              <p>{run.brand.vision}</p>
              <div className="detail-block">
                <span className="detail-label">Value</span>
                <p>{run.brand.value}</p>
              </div>
              <div className="detail-block">
                <span className="detail-label">Voice</span>
                <p>{run.brand.voice}</p>
              </div>
              <div className="detail-block">
                <span className="detail-label">Imagery</span>
                <ul>
                  {run.brand.brand_imagery.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
              <div className="palette-row">
                {run.brand.color_palette_hex.map((color) => (
                  <div key={color} className="palette-chip">
                    <span className="palette-swatch" style={{ backgroundColor: color }} />
                    {color}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="empty-state">Brand direction appears after research approval.</div>
          )}
        </article>
      </section>

      <section className="panel">
        <div className="panel-header">
          <p className="eyebrow">Files</p>
          <h3 className="section-title">Generated site package</h3>
        </div>

        {run.site ? (
          <div className="file-list">
            {run.site.files.map((file) => (
              <div key={file.path} className="file-row">
                <span>{file.path}</span>
                <span>{file.media_type || 'text/plain'}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">No site files yet.</div>
        )}
      </section>
    </div>
  )
}
