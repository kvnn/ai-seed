import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { ApiError } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, bootstrap } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showBootstrap, setShowBootstrap] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const redirectTarget = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/studio'

  const handleLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await login(email, password)
      navigate(redirectTarget, { replace: true })
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        setError(requestError.message)
      } else {
        setError('Sign in failed.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleBootstrap = async () => {
    setError(null)
    setLoading(true)

    try {
      await bootstrap(email, password)
      navigate('/studio', { replace: true })
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        setError(requestError.message)
      } else {
        setError('Bootstrap failed.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <p className="eyebrow">Workshop operator access</p>
        <h1 className="auth-title">Enter the seed workspace</h1>
        <p className="auth-copy">Sign in to manage student project runs, review generated artifacts, and publish previews.</p>

        <form className="auth-form" onSubmit={handleLogin}>
          <label className="field">
            <span>Email</span>
            <input
              autoComplete="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="operator@example.com"
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimum 8 characters"
            />
          </label>

          {error ? <div className="banner banner-error">{error}</div> : null}

          <button className="button button-primary" type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="auth-footer">
          <span>Need an invite-based account?</span>
          <Link to="/register">Register</Link>
        </div>

        <button className="link-button" type="button" onClick={() => setShowBootstrap((value) => !value)}>
          {showBootstrap ? 'Hide bootstrap admin' : 'Fresh stack? Bootstrap the first admin'}
        </button>

        {showBootstrap ? (
          <div className="bootstrap-panel">
            <p>Create the first admin account on an empty database using the same email and password above.</p>
            <button className="button button-ghost" type="button" disabled={loading} onClick={() => void handleBootstrap()}>
              {loading ? 'Bootstrapping...' : 'Bootstrap admin'}
            </button>
          </div>
        ) : null}
      </div>
    </div>
  )
}
