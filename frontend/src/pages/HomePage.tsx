import { Link } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { SeoMeta } from '../components/SeoMeta'

type Track = {
  number: string
  title: string
  summary: string
  examples: string
}

const tracks: Track[] = [
  {
    number: '01',
    title: 'Static Website',
    summary: 'Ship a clean, live site so you publish something real before adding complexity.',
    examples: 'Portfolio, freelancer site, local business page',
  },
  {
    number: '02',
    title: 'Web App',
    summary: 'Add forms, backend logic, and storage to turn your site into software.',
    examples: 'Signup funnel, directory, resource board',
  },
  {
    number: '03',
    title: 'A.I. Workflow App',
    summary: 'Layer an LLM workflow so the app can interpret, generate, and act on user input.',
    examples: 'Intake summaries, content generation, notes-to-email',
  },
]

type Pattern = {
  name: string
  oneLiner: string
}

const patterns: Pattern[] = [
  { name: 'Crawl-Cache-Generate', oneLiner: 'Scrape, cache, and feed content to LLMs' },
  { name: 'LLM Agent Factory', oneLiner: 'Structured output via Pydantic schemas and cost tracking' },
  { name: 'SSE Streaming', oneLiner: 'Real-time progress during long LLM generations' },
  { name: 'Storage Backend Swap', oneLiner: 'Local filesystem to S3 without code changes' },
  { name: 'Custom Domain Lifecycle', oneLiner: 'DNS validation and CDN provisioning state machine' },
  { name: 'Async DB Patterns', oneLiner: 'Dual sync/async SQLAlchemy with pool tuning' },
]

const steps = [
  {
    label: 'Clone',
    command: 'git clone <this-repo> my-project && cd my-project',
    detail: 'Start every new project from this seed.',
  },
  {
    label: 'Configure',
    command: 'cp .env.example .env   # add your API keys',
    detail: 'OpenAI, Firecrawl, and AWS S3 keys go here. Ask your workshop lead if you need vendor credentials.',
  },
  {
    label: 'Articulate',
    command: 'claude',
    detail: 'Open Claude Code in your project. It will prompt you to articulate your project vision and save it to docs/VISION.md.',
  },
  {
    label: 'Build',
    command: 'docker compose up',
    detail: 'The stack runs locally: Vite frontend + FastAPI backend + SQLite. Deploy to Render when ready.',
  },
]

export default function HomePage() {
  const { user } = useAuth()

  return (
    <div className="auth-shell">
      <SeoMeta
        title="OahuAI Seed — Build LLM Workflow Apps"
        description="A proven starter repo for building simple, comprehensive LLM workflow apps. Clone, articulate your vision, and ship."
        imagePath="/SubMainImage-01.jpg"
      />

      <div className="page-stack home-width">
        {/* Hero */}
        <section className="hero-panel panel">
          <div className="hero-copy">
            <p className="eyebrow">OahuAI Seed</p>
            <h1 className="hero-title">
              A starting point for building LLM workflow apps.
            </h1>
            <p className="hero-body">
              Three years of applied-AI web app patterns distilled into one cloneable repo.
              Clone it, describe your vision, and let Claude Code build the rest.
            </p>
            <div className="hero-metrics">
              <div className="metric-card">
                <span className="metric-label">Stack</span>
                <span className="metric-value">FastAPI + Vite + Pydantic AI</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Patterns</span>
                <span className="metric-value">6 proven architectures</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Deploy</span>
                <span className="metric-value">Render + S3</span>
              </div>
            </div>
            <div className="cta-row">
              <a className="button button-primary" href="#get-started">Get started</a>
              <Link className="button button-ghost" to={user ? '/studio' : '/login'}>
                {user ? 'Open studio' : 'Sign in'}
              </Link>
            </div>
          </div>
          <div className="hero-visual">
            <img src="/SubMainImage-01.jpg" alt="AI workflow visualization" className="hero-image" />
          </div>
        </section>

        {/* Three tracks */}
        <section>
          <div className="panel-header">
            <p className="eyebrow">Build progression</p>
            <h2 className="section-title">Three exercises, one evening</h2>
            <p className="section-copy">
              Each track builds on the last. You ship something real at every step.
            </p>
          </div>
          <div className="card-grid track-grid">
            {tracks.map((track) => (
              <div key={track.number} className="track-card">
                <span className="track-number">{track.number}</span>
                <h3>{track.title}</h3>
                <p>{track.summary}</p>
                <span className="track-examples">{track.examples}</span>
              </div>
            ))}
          </div>
        </section>

        {/* What's included */}
        <section className="home-grid">
          <article className="panel">
            <div className="panel-header">
              <p className="eyebrow">Included patterns</p>
              <h2 className="section-title">Battle-tested architectures</h2>
              <p className="section-copy">
                Each pattern is a self-contained doc with problem, solution, code, pitfalls, and an
                adaptation guide. Point Claude Code at the relevant pattern and it builds the right
                implementation for your context.
              </p>
            </div>
            <div className="pattern-list">
              {patterns.map((p) => (
                <div key={p.name} className="pattern-row">
                  <span className="pattern-name">{p.name}</span>
                  <span className="pattern-desc">{p.oneLiner}</span>
                </div>
              ))}
            </div>
          </article>

          <article className="panel">
            <div className="panel-header">
              <p className="eyebrow">What you get</p>
              <h2 className="section-title">Ready to build on</h2>
            </div>
            <div className="schedule-list">
              <div className="schedule-item">
                <span className="schedule-time">Auth</span>
                <p>Session-based authentication with admin bootstrap and invite codes.</p>
              </div>
              <div className="schedule-item">
                <span className="schedule-time">Database</span>
                <p>SQLAlchemy models. SQLite locally, Postgres in production.</p>
              </div>
              <div className="schedule-item">
                <span className="schedule-time">Storage</span>
                <p>Swappable file storage — local filesystem for dev, S3 for production.</p>
              </div>
              <div className="schedule-item">
                <span className="schedule-time">Frontend</span>
                <p>React + TypeScript + Vite with a warm, editorial design system.</p>
              </div>
              <div className="schedule-item">
                <span className="schedule-time">LLM agents</span>
                <p>Pydantic AI agent patterns with structured output, cost tracking, and SSE streaming.</p>
              </div>
              <div className="schedule-item">
                <span className="schedule-time">Deploy</span>
                <p>Docker Compose for local dev. Ready for Render, Railway, or any container host.</p>
              </div>
            </div>
          </article>
        </section>

        {/* Getting started */}
        <section className="panel" id="get-started">
          <div className="panel-header">
            <p className="eyebrow">Get started</p>
            <h2 className="section-title">Four steps to your first build</h2>
          </div>
          <div className="steps-grid">
            {steps.map((step, i) => (
              <div key={step.label} className="step-card">
                <span className="step-number">{String(i + 1).padStart(2, '0')}</span>
                <h3 className="step-label">{step.label}</h3>
                <code className="step-command">{step.command}</code>
                <p className="step-detail">{step.detail}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Vision prompt */}
        <section className="panel panel-vision">
          <div className="panel-header">
            <p className="eyebrow">First conversation with Claude Code</p>
            <h2 className="section-title">Articulate your vision</h2>
            <p className="section-copy">
              When you open Claude Code in this repo, it will ask you to describe what you want to
              build, who it's for, and what "done" looks like. Your answers get saved to{' '}
              <code>docs/VISION.md</code> — a living document that keeps every future conversation
              grounded in your intent.
            </p>
          </div>
          <div className="terminal-panel vision-terminal">
            <pre className="terminal-window">
              <span className="terminal-line">$ claude</span>
              <span className="terminal-line">&nbsp;</span>
              <span className="terminal-line">{'> Let\'s articulate your vision for this project.'}</span>
              <span className="terminal-line">{'> What problem are you solving, and for whom?'}</span>
              <span className="terminal-line">{'> What does "done" look like for the first version?'}</span>
              <span className="terminal-line">{'> What constraints should I know about?'}</span>
            </pre>
          </div>
        </section>

        {/* Footer */}
        <footer className="seed-footer">
          <p>
            Built by <strong>OahuAI</strong> from 3 years of applied-AI web app development.
            <br />
            Designed for the <em>Claude Code 101</em> workshop series.
          </p>
        </footer>
      </div>
    </div>
  )
}
