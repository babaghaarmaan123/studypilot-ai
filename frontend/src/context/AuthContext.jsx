import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import api, { clearToken, getToken, onUnauthorized, setToken } from '@/lib/api'
import { useTheme } from '@/context/ThemeContext'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(getToken()))
  const { setTheme } = useTheme()
  const syncedTheme = useRef(false)

  const signOut = useCallback(() => {
    clearToken()
    setUser(null)
    syncedTheme.current = false
  }, [])

  // A 401 from anywhere means the token is dead — drop it.
  useEffect(() => {
    onUnauthorized(() => {
      clearToken()
      setUser(null)
    })
  }, [])

  const loadUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      setLoading(false)
      return null
    }
    try {
      const me = await api.auth.me()
      setUser(me)
      return me
    } catch {
      clearToken()
      setUser(null)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  // Adopt the theme saved on the account, once, after sign-in.
  useEffect(() => {
    if (user?.settings?.theme && !syncedTheme.current) {
      syncedTheme.current = true
      setTheme(user.settings.theme)
    }
  }, [user, setTheme])

  const signIn = useCallback(async ({ email, password, rememberMe }) => {
    const data = await api.auth.login({ email, password, remember_me: !!rememberMe })
    setToken(data.access_token, !!rememberMe)
    setUser(data.user)
    return data.user
  }, [])

  const signUp = useCallback(async ({ name, email, password }) => {
    const data = await api.auth.register({ name, email, password })
    setToken(data.access_token, true)
    setUser(data.user)
    return data.user
  }, [])

  /** Merge a partial user object into state (after a profile PATCH, say). */
  const patchUser = useCallback((partial) => {
    setUser((current) => (current ? { ...current, ...partial } : current))
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      needsOnboarding: Boolean(user) && !user.onboarding_completed,
      signIn,
      signUp,
      signOut,
      refresh: loadUser,
      patchUser,
      setUser,
    }),
    [user, loading, signIn, signUp, signOut, loadUser, patchUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
