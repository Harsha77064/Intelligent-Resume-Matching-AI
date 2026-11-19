import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { auth } from '../api'
import { Loading } from './ui'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

export const homeFor = (role) => (role === 'hr' ? '/' : '/portal')
export const roleForPath = (path = '') => (path.startsWith('/portal') ? 'candidate' : 'hr')
export const loginPathFor = (role) => (role === 'hr' ? '/hr/login' : '/login')
export const forgotPathFor = (role) => (role === 'hr' ? '/hr/forgot-password' : '/forgot-password')

/**
 * A browser can hold two independent sessions: one HR and one candidate.
 * sessions = { hr: user|null, candidate: user|null }  (undefined while loading)
 */
export function AuthProvider({ children }) {
  const [sessions, setSessions] = useState(undefined)

  const refresh = useCallback(
    () => auth.me().then(setSessions).catch(() => setSessions({ hr: null, candidate: null })),
    [],
  )
  useEffect(() => { refresh() }, [refresh])
  useEffect(() => {
    // a 401 means a session expired or was signed out in another tab: re-check
    window.addEventListener('mp:unauthorized', refresh)
    // keep tabs in sync when the user comes back to this one
    window.addEventListener('focus', refresh)
    return () => {
      window.removeEventListener('mp:unauthorized', refresh)
      window.removeEventListener('focus', refresh)
    }
  }, [refresh])

  const login = async (email, password, role) => {
    const u = await auth.login(email, password, role)
    setSessions((s) => ({ ...(s || {}), [u.role]: u }))
    return u
  }
  const register = async (name, email, password) => {
    const u = await auth.register(name, email, password)
    setSessions((s) => ({ ...(s || {}), candidate: u }))
    return u
  }
  const logout = async (role) => {
    await auth.logout(role).catch(() => {})
    setSessions((s) => ({ ...(s || {}), [role]: null }))
  }

  return <AuthCtx.Provider value={{ sessions, login, register, logout, refresh }}>{children}</AuthCtx.Provider>
}

/** Renders children only when this browser has a session for `role`; otherwise goes to login. */
export function RequireRole({ role, children }) {
  const { sessions } = useAuth()
  const loc = useLocation()
  if (sessions === undefined) return <div className="min-h-screen"><Loading text="Checking your session…" /></div>
  if (!sessions[role]) return <Navigate to={loginPathFor(role)} replace state={{ from: loc.pathname }} />
  return children
}

/** The signed-in user for the dashboard currently on screen. */
export function useRoleUser(role) {
  const { sessions } = useAuth()
  return sessions?.[role] || null
}
