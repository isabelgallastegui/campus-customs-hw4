import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { PublicUser } from './auth'

const STORAGE_KEY = 'campus-customs-user'

interface AuthValue {
  user: PublicUser | null
  signIn: (user: PublicUser) => void
  signOut: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

/**
 * Holds the signed-in user for the session. Only the public profile is kept —
 * the password and its hash never reach the browser.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<PublicUser | null>(null)

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY)
    if (!saved) return
    try {
      setUser(JSON.parse(saved) as PublicUser)
    } catch {
      window.localStorage.removeItem(STORAGE_KEY)
    }
  }, [])

  const signIn = useCallback((nextUser: PublicUser) => {
    setUser(nextUser)
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextUser))
  }, [])

  const signOut = useCallback(() => {
    setUser(null)
    window.localStorage.removeItem(STORAGE_KEY)
  }, [])

  const value = useMemo(() => ({ user, signIn, signOut }), [user, signIn, signOut])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside an AuthProvider')
  return context
}
