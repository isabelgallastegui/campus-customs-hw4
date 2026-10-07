import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PASSWORD_RULES, passwordMeetsRules, signup } from '../auth'
import { useAuth } from '../AuthContext'

export default function CreateAccount() {
  const navigate = useNavigate()
  const { signIn } = useAuth()

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const rulesMet = passwordMeetsRules(password)
  const passwordsMatch = password.length > 0 && password === confirmPassword
  const canSubmit =
    firstName.trim() !== '' &&
    lastName.trim() !== '' &&
    email.trim() !== '' &&
    rulesMet &&
    passwordsMatch &&
    !submitting

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)

    if (!passwordsMatch) {
      setError('The two passwords do not match.')
      return
    }
    if (!rulesMet) {
      setError('Your password does not meet all of the requirements yet.')
      return
    }

    setSubmitting(true)
    try {
      const user = await signup({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
        password,
        confirm_password: confirmPassword,
      })
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
        <p className="eyebrow">Join the shop</p>
        <h1>Create account</h1>
        <p>
          One account keeps your sizes, your favorites, and your conversation with Bulldog in one
          place.
        </p>

        <form onSubmit={handleSubmit} noValidate>
          <div className="field-row">
            <div className="field">
              <label htmlFor="signup-first">First name</label>
              <input
                id="signup-first"
                autoComplete="given-name"
                placeholder="Ada"
                value={firstName}
                onChange={(event) => setFirstName(event.target.value)}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="signup-last">Last name</label>
              <input
                id="signup-last"
                autoComplete="family-name"
                placeholder="Lovelace"
                value={lastName}
                onChange={(event) => setLastName(event.target.value)}
                required
              />
            </div>
          </div>

          <div className="field">
            <label htmlFor="signup-email">Email</label>
            <input
              id="signup-email"
              type="email"
              autoComplete="email"
              placeholder="you@yale.edu"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>

          <div className="field">
            <label htmlFor="signup-password">Password</label>
            <input
              id="signup-password"
              type="password"
              autoComplete="new-password"
              placeholder="Choose something sturdy"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          <ul className="rules" aria-label="Password requirements">
            {PASSWORD_RULES.map((rule) => {
              const met = rule.test(password)
              return (
                <li key={rule.label} className={met ? 'rule met' : 'rule'}>
                  <span className="rule-mark" aria-hidden="true">
                    {met ? '✓' : '○'}
                  </span>
                  {rule.label}
                </li>
              )
            })}
          </ul>

          <div className="field">
            <label htmlFor="signup-confirm">Confirm password</label>
            <input
              id="signup-confirm"
              type="password"
              autoComplete="new-password"
              placeholder="Type it once more"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
            />
            {confirmPassword.length > 0 && (
              <p className={passwordsMatch ? 'field-hint ok' : 'field-hint bad'}>
                {passwordsMatch ? 'Passwords match.' : 'Passwords do not match yet.'}
              </p>
            )}
          </div>

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          <button type="submit" className="btn auth-submit" disabled={!canSubmit}>
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="auth-alt">
          Already have one? <Link to="/login">Log in</Link>
        </p>
      </section>
    </div>
  )
}
