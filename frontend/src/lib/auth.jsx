import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, getToken, setRefresh, setToken } from './apiClient.js'

const Ctx = createContext(null)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!getToken()) { setReady(true); return }
    api('/auth/me').then(setUser).catch(() => setToken(null)).finally(() => setReady(true))
  }, [])
  useEffect(() => {
    const out = () => setUser(null)
    window.addEventListener('brandsure:logout', out)
    return () => window.removeEventListener('brandsure:logout', out)
  }, [])

  const login = useCallback(async (email, password) => {
    const r = await api('/auth/login', { method: 'POST', body: { email, password } })
    setToken(r.token); setRefresh(r.refresh_token); setUser(r.user)
  }, [])
  const register = useCallback(async (payload) => {
    const r = await api('/auth/register', { method: 'POST', body: payload })
    if (!r.token) return r.message // e-mail confirmation is on: sign in after confirming
    setToken(r.token); setRefresh(r.refresh_token); setUser(r.user)
    return null
  }, [])
  const demoLogin = useCallback(async (role) => {
    const r = await api('/demo/login', { method: 'POST', body: { role } })
    setToken(r.token); setRefresh(null); setUser(r.user)
  }, [])
  const logout = useCallback(() => { setToken(null); setRefresh(null); setUser(null) }, [])
  const value = useMemo(() => ({ user, ready, login, register, demoLogin, logout }), [user, ready, login, register, demoLogin, logout])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
