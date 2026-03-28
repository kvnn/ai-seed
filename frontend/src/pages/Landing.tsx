import { useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'

import type { AppOutletContext } from '../App'
import { api, ApiError } from '../api/client'
import type { RunCreateRequest } from '../api/types'
import { SeoMeta } from '../components/SeoMeta'
import { formatDateTime, summarizeBrief } from '../utils/time'

type Track = {
  id: 'static-website' | 'web-app' | 'ai-workflow'
  number: string
  title: string
  summary: string
  examples: string
}

const tracks: Track[] = [
  {
    id: 'static-website',
    number: '01',
    title: 'Static Website',
    summary: 'Ship a clean, live site first so students publish something real before adding complexity.',
    examples: 'Portfolio, freelancer site, local business page',
  },
  {
    id: 'web-app',
    number: '02',
    title: 'Web App',
    summary: 'Add forms, backend logic, storage, and public-data import to turn a site into software.',
    examples: 'Signup funnel, registration form, directory, resource board',
  },
  {
    id: 'ai-workflow',
    number: '03',
    title: 'A.I. Workflow App',
    summary: 'Layer an LLM workflow into the app so it can interpret, generate, and act on user input.',
    examples: 'Intake summaries, qualified leads, notes-to-email workflows',
  },
]

function parseLines(value: string) {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

export default function Landing() {
  const navigate = useNavigate()
  const { runs, refreshRuns } = useOutletContext<AppOutletContext>()
  const [selectedTrack, setSelectedTrack] = useState<Track['id']>('static-website')
  const [brief, setBrief] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  const [preferredStyle, setPreferredStyle] = useState('minimal, warm, editorial')
  const [publishSlug, setPublishSlug] = useState('')
  const [requiredFacts, setRequiredFacts] = useState('')
  const [bannedClaims, setBannedClaims] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const selectedTrackData = tracks.find((track) => track.id === selectedTrack) || tracks[0]

  const handleCreateRun = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    if (brief.trim().length < 12) {
      setError('Add a clearer project brief so the workshop flow has enough direction to generate work.')
      return
    }

    const payload: RunCreateRequest = {
      brief: `${selectedTrackData.title}: ${brief.trim()}`,
      preferred_style: preferredStyle.trim() || undefined,
      publish_slug: publishSlug.trim() || undefined,
      required_facts: parseLines(requiredFacts),
      banned_claims: parseLines(bannedClaims),
    }

    if (sourceUrl.trim()) {
      payload.source_url = sourceUrl.trim()
    }

    setSubmitting(true)

    try {
      const run = await api.createRun(payload)
      await refreshRuns()
      navigate(`/studio/runs/${run.id}`)
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        setError(requestError.message)
      } else {
        setError('The workshop project could not be created.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-stack">
      <SeoMeta
        title="OahuAI Seed Workshop"
        description="Launch a static site, a web app, and an AI workflow app through one guided workshop workspace."
        imagePath="/SubMainImage-01.jpg"
      />

      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Requirements-driven workshop</p>
          <h2 className="hero-title">First you publish something. Then you make it interactive. Then you make it intelligent.</h2>
          <p className="hero-body">
            This workspace is the operator console for the workshop. Each run turns a project brief into research,
            brand direction, a generated site preview, and a publishable path your students can actually ship.
          </p>
          <div className="hero-metrics">
            <div className="metric-card">
              <span className="metric-label">Cost</span>
              <span className="metric-value">$100</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Schedule</span>
              <span className="metric-value">6pm to 9pm</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Outcome</span>
              <span className="metric-value">3 shipped exercises</span>
            </div>
          </div>
        </div>
        <div className="hero-visual">
          <img src="/SubMainImage-01.jpg" alt="Workshop preview collage" className="hero-image" />
        </div>
      </section>

      <section className="card-grid track-grid">
        {tracks.map((track) => (
          <button
            key={track.id}
            type="button"
            className={`track-card${track.id === selectedTrack ? ' is-selected' : ''}`}
            onClick={() => setSelectedTrack(track.id)}
          >
            <span className="track-number">{track.number}</span>
            <h3>{track.title}</h3>
            <p>{track.summary}</p>
            <span className="track-examples">{track.examples}</span>
          </button>
        ))}
      </section>

      <section className="card-grid landing-grid">
        <article className="panel panel-form">
          <div className="panel-header">
            <p className="eyebrow">Start a project run</p>
            <h3 className="section-title">{selectedTrackData.title}</h3>
            <p className="section-copy">
              Define the job, lock constraints, and generate a deployable baseline for the selected workshop exercise.
            </p>
          </div>

          <form className="project-form" onSubmit={handleCreateRun}>
            <label className="field">
              <span>Project brief</span>
              <textarea
                value={brief}
                onChange={(event) => setBrief(event.target.value)}
                placeholder="Describe the student project, intended audience, offer, and what done looks like."
                rows={5}
              />
            </label>

            <label className="field">
              <span>Source URL</span>
              <input
                value={sourceUrl}
                onChange={(event) => setSourceUrl(event.target.value)}
                placeholder="Optional reference site or source material"
                type="url"
              />
            </label>

            <div className="field-row">
              <label className="field">
                <span>Preferred style</span>
                <input
                  value={preferredStyle}
                  onChange={(event) => setPreferredStyle(event.target.value)}
                  placeholder="minimal, warm, editorial"
                />
              </label>
              <label className="field">
                <span>Publish slug</span>
                <input
                  value={publishSlug}
                  onChange={(event) => setPublishSlug(event.target.value)}
                  placeholder="student-project"
                />
              </label>
            </div>

            <div className="field-row">
              <label className="field">
                <span>Required facts</span>
                <textarea
                  value={requiredFacts}
                  onChange={(event) => setRequiredFacts(event.target.value)}
                  placeholder="One fact per line"
                  rows={4}
                />
              </label>
              <label className="field">
                <span>Banned claims</span>
                <textarea
                  value={bannedClaims}
                  onChange={(event) => setBannedClaims(event.target.value)}
                  placeholder="One caution per line"
                  rows={4}
                />
              </label>
            </div>

            {error ? <div className="banner banner-error">{error}</div> : null}

            <div className="form-footer">
              <div className="helper-copy">
                Students leave with a repeatable loop: requirements, plan, build, run, improve.
              </div>
              <button className="button button-primary" type="submit" disabled={submitting}>
                {submitting ? 'Creating run...' : 'Create workshop run'}
              </button>
            </div>
          </form>
        </article>

        <article className="panel panel-sidebar">
          <div className="panel-header">
            <p className="eyebrow">Workshop shape</p>
            <h3 className="section-title">What students ship tonight</h3>
          </div>
          <div className="schedule-list">
            <div className="schedule-item">
              <span className="schedule-time">6pm to 7pm</span>
              <p>Get the software stack running locally, connect required accounts, and publish a static website.</p>
            </div>
            <div className="schedule-item">
              <span className="schedule-time">7pm to 8pm</span>
              <p>Run tight build loops until the web app baseline is deployment-ready.</p>
            </div>
            <div className="schedule-item">
              <span className="schedule-time">8pm to 9pm</span>
              <p>Add an AI workflow and adapt the template to each student’s real problem.</p>
            </div>
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="panel-header">
          <p className="eyebrow">Recent runs</p>
          <h3 className="section-title">Current project queue</h3>
        </div>

        {runs.length === 0 ? (
          <div className="empty-state">No workshop runs yet. Start the first project from the form above.</div>
        ) : (
          <div className="run-grid">
            {runs.slice(0, 6).map((run) => (
              <button
                key={run.id}
                type="button"
                className="run-card"
                onClick={() => navigate(`/runs/${run.id}`)}
              >
                <div className="run-card-top">
                  <span className={`status-pill status-${run.status}`}>{run.status.replace(/_/g, ' ')}</span>
                  <span className="run-card-date">{formatDateTime(run.updated_at)}</span>
                </div>
                <h4>{summarizeBrief(run.brief)}</h4>
                <p>{run.source_url || run.publish_slug}</p>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
