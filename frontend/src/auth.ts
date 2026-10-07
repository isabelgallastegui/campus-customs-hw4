/** Account signup/login against the FastAPI backend. */

export interface PublicUser {
  id: number
  name: string
  email: string
  first_name: string | null
  last_name: string | null
  created_at: string
}

export interface SignupPayload {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

/** FastAPI puts the human-readable message in `detail`. */
async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const detail = (data as { detail?: unknown } | null)?.detail
    if (typeof detail === 'string') throw new Error(detail)
    // Pydantic field errors arrive as a list of objects.
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string }
      throw new Error(first.msg ?? 'Please check the form and try again.')
    }
    throw new Error('Something went wrong. Please try again.')
  }

  return data as T
}

export function signup(payload: SignupPayload): Promise<PublicUser> {
  return postJson<PublicUser>('/api/auth/signup', payload)
}

export function login(email: string, password: string): Promise<PublicUser> {
  return postJson<PublicUser>('/api/auth/login', { email, password })
}

/**
 * The same rules the backend enforces, mirrored here so the form can show
 * live feedback. The backend remains the authority — it re-checks every rule.
 */
export const PASSWORD_RULES: { label: string; test: (value: string) => boolean }[] = [
  { label: 'At least 8 characters', test: (v) => v.length >= 8 },
  { label: 'At least one uppercase letter', test: (v) => /[A-Z]/.test(v) },
  { label: 'At least one lowercase letter', test: (v) => /[a-z]/.test(v) },
  { label: 'At least one number', test: (v) => /[0-9]/.test(v) },
]

export function passwordMeetsRules(value: string): boolean {
  return PASSWORD_RULES.every((rule) => rule.test(value))
}
