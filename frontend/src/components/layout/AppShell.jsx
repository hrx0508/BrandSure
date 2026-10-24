import { useEffect, useRef, useState } from 'react'
import { Navigate, NavLink, Outlet, useLocation } from 'react-router-dom'
import { api } from '../../lib/apiClient.js'
import { useAuth } from '../../lib/auth.jsx'
import { ROLE_LABEL } from '../../lib/formatters.js'
import { gsap, reduced } from '../../lib/motion.js'
import { Spinner } from '../ui/index.jsx'

const THEME_KEY = 'brandsure.theme'
function applyTheme(t) { if (t) document.documentElement.dataset.theme = t }

export default function AppShell() {
  const { user, ready, logout, demoLogin } = useAuth()
  const [demoBusy, setDemoBusy] = useState(false)
  const [health, setHealth] = useState(null)
  const main = useRef(null)
  const loc = useLocation()

  useEffect(() => { try { applyTheme(localStorage.getItem(THEME_KEY)) } catch { /* ignore */ } }, [])
  useEffect(() => { if (user) api('/health').then(setHealth).catch(() => {}) }, [user])
  useEffect(() => {
    if (reduced() || !main.current) return
    gsap.fromTo(main.current, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.35, ease: 'power2.out', clearProps: 'transform,opacity' })
  }, [loc.pathname])

  if (!ready) return <Spinner label="Starting BrandSure…" />
  if (!user) return <Navigate to="/login" replace />

  const toggle = () => {
    const dark = (document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')) === 'dark'
    const next = dark ? 'light' : 'dark'
    applyTheme(next)
    try { localStorage.setItem(THEME_KEY, next) } catch { /* ignore */ }
  }
  const isDemo = !!health?.demo_login && user.email?.endsWith('@brandsure.demo')
  const switchRole = async (role) => { setDemoBusy(true); try { await demoLogin(role); window.location.assign('/') } finally { setDemoBusy(false) } }
  const resetDemo = async () => {
    if (!window.confirm('Reset the demo? All changes you made are removed and the sample posts come back.')) return
    setDemoBusy(true)
    try { await api('/demo/reset', { method: 'POST' }); window.location.assign('/') } finally { setDemoBusy(false) }
  }
  const NAV = {
    admin: [['/', 'Home'], ['/brand-kits', 'Brand Kits'], ['/posts', 'All posts'], ['/insights', 'Insights'], ['/team', 'Team'], ['/settings', 'Integrations'], ['/guide', 'How it works']],
    creator: [['/', 'Home'], ['/posts', 'My posts'], ['/brand-kits', 'Brand rules'], ['/guide', 'How it works']],
    reviewer: [['/', 'Home'], ['/posts', 'Review queue'], ['/brand-kits', 'Brand rules'], ['/insights', 'Insights'], ['/guide', 'How it works']],
  }
  const nav = NAV[user.role]
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line backdrop-blur" style={{ background: 'color-mix(in srgb, var(--bg) 82%, transparent)' }}>
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4">
          <div className="flex items-center gap-2 text-xl font-extrabold">
            <i className="inline-block h-6 w-6 rounded-lg" style={{ background: 'linear-gradient(135deg, var(--brand), var(--mint))' }} />
            BrandSure
          </div>
          <nav aria-label="Main" className="flex gap-1 overflow-x-auto">
            {nav.map(([to, label]) => (
              <NavLink key={to} to={to} end={to === '/'}
                className={({ isActive }) => `rounded-xl px-3 py-2 text-sm font-semibold whitespace-nowrap ${isActive ? 'bg-soft text-brand' : 'text-mut hover:text-ink'}`}>
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <span className="hidden text-right text-xs leading-tight md:block"><b>{user.display_name}</b><br /><span className="text-mut">{ROLE_LABEL[user.role]}</span></span>
            <button className="btn-alt" onClick={toggle} aria-label="Switch between light and dark theme">◐</button>
            <button className="btn-alt" onClick={logout}>Sign out</button>
          </div>
        </div>
      </header>
      {isDemo && (
        <div role="region" aria-label="Demo mode" className="border-b border-line" style={{ background: 'var(--soft)' }}>
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-2 px-4 py-2 text-sm">
            <b>Demo mode</b><span className="text-mut">You are the {ROLE_LABEL[user.role]}. Switch role:</span>
            {['admin', 'creator', 'reviewer'].map((r) => (
              <button key={r} disabled={demoBusy || user.role === r} onClick={() => switchRole(r)} className="btn-alt !py-1" aria-pressed={user.role === r}
                style={user.role === r ? { background: 'var(--brand)', color: 'var(--brand-ink)', borderColor: 'var(--brand)' } : undefined}>{ROLE_LABEL[r]}</button>))}
            <button disabled={demoBusy} onClick={resetDemo} className="ml-auto text-xs text-mut underline">Reset demo data</button>
          </div>
        </div>)}
      <main ref={main} className="mx-auto max-w-6xl px-4 py-8"><Outlet /></main>
      {health && (
        <footer className="mx-auto max-w-6xl px-4 pb-10 text-xs text-mut">
          <b>AI disclosure:</b> {health.ai_notice} “No issues detected” means only that the configured checks found nothing; it is not a guarantee of compliance.
        </footer>
      )}
    </div>
  )
}
