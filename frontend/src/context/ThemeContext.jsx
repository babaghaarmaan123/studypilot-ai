import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

const ThemeContext = createContext(null)
const STORAGE_KEY = 'studypilot-theme'

function systemPrefersDark() {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

function readStoredTheme() {
  try {
    return localStorage.getItem(STORAGE_KEY) || 'system'
  } catch {
    return 'system'
  }
}

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(readStoredTheme)
  const [isDark, setIsDark] = useState(
    () => theme === 'dark' || (theme === 'system' && systemPrefersDark()),
  )

  const applyTheme = useCallback((next) => {
    const dark = next === 'dark' || (next === 'system' && systemPrefersDark())
    document.documentElement.classList.toggle('dark', dark)
    document.documentElement.style.colorScheme = dark ? 'dark' : 'light'
    setIsDark(dark)
  }, [])

  useEffect(() => {
    applyTheme(theme)
    try {
      localStorage.setItem(STORAGE_KEY, theme)
    } catch {
      /* storage unavailable */
    }
  }, [theme, applyTheme])

  // Follow the OS while the preference is "system".
  useEffect(() => {
    if (theme !== 'system') return undefined
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => applyTheme('system')
    query.addEventListener('change', handler)
    return () => query.removeEventListener('change', handler)
  }, [theme, applyTheme])

  const value = useMemo(
    () => ({
      theme,
      isDark,
      setTheme: setThemeState,
      toggleTheme: () => setThemeState(isDark ? 'light' : 'dark'),
    }),
    [theme, isDark],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme must be used inside <ThemeProvider>')
  return context
}
