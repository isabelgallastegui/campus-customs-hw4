import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login } from '../auth'
import { useAuth } from '../AuthContext'

export default function Login() {
  const navigate = useNavigate()
  const { signIn } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      const user = await login(email.trim(), password)
      signIn(user)
      navigate('/')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="container auth-wrap">
      <section className="auth-card">
        <p className="eyebrow">Welcome back</p>
        <h1>Log in</h1>
        <p>Pick up where you left off — your saved styles and past chats come with you.</p>

        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              placeholder="you@yale.edu"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>

          <div className="field">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="btn auth-submit"
            disabled={submitting || email.trim() === '' || password === ''}
          >
            {submitting ? 'Checking…' : 'Log in'}
          </button>
        </form>

        <p className="auth-alt">
          New to the shop? <Link to="/create-account">Create an account</Link>
        </p>
      </section>
    </div>
  )
}
