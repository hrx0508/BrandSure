
import { useEffect, useRef, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { api } from '../../lib/apiClient.js'
import { useAuth } from '../../lib/auth.jsx'
import { gsap, reduced } from '../../lib/motion.js'
import { Button, ErrorBanner } from '../../components/ui/index.jsx'

const DEMO_ROLES = [
  ['admin', 'Admin', 'Set up the Brand Kit: guidelines, rules, send to creators.'],
  ['creator', 'Creator', 'Write a post, see its faults, fix them, send it to a reviewer.'],
  ['reviewer', 'Reviewer', 'Review a post: suggest, edit, approve, send back or reject.'],
]

export default function Login() {
  const { user, login, register, demoLogin } = useAuth()

  const [mode, setMode] = useState('login')
  const [f, setF] = useState({
    email: '',
    password: '',
    display_name: '',
    organisation_name: '',
  })
  const [health, setHealth] = useState(null)
  const [healthLoading, setHealthLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [info, setInfo] = useState('')
  const root = useRef(null)

  // Load backend capabilities without blocking the login form.
  useEffect(() => {
    let active = true

    api('/health')
      .then((data) => {
        if (active) setHealth(data)
      })
      .catch((error) => {
        if (active) setErr(error)
      })
      .finally(() => {
        if (active) setHealthLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  // Preserve the existing motion design.
  useEffect(() => {
    if (reduced() || !root.current) return undefined

    const ctx = gsap.context(() => {
      gsap.from('.reveal', {
        y: 24,
        opacity: 0,
        stagger: 0.1,
        duration: 0.6,
        ease: 'power3.out',
      })

      gsap.to('.blob-a', {
        x: 40,
        y: 30,
        duration: 6,
        yoyo: true,
        repeat: -1,
        ease: 'sine.inOut',
      })

      gsap.to('.blob-b', {
        x: -50,
        y: -20,
        duration: 7,
        yoyo: true,
        repeat: -1,
        ease: 'sine.inOut',
      })
    }, root)

    return () => ctx.revert()
  }, [])

  if (user) return <Navigate to="/" replace />

  const set = (key) => (event) => {
    setF((previous) => ({
      ...previous,
      [key]: event.target.value,
    }))
  }

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setErr(null)
    setInfo('')

    try {
      if (mode === 'login') {
        await login(f.email, f.password)
      } else {
        const message = await register(f)

        if (message) {
          setInfo(message)
          setMode('login')
        }
      }
    } catch (error) {
      setErr(error)
    } finally {
      setBusy(false)
    }
  }

  async function demo(role) {
    setBusy(true)
    setErr(null)
    setInfo('')

    try {
      await demoLogin(role)
    } catch (error) {
      setErr(error)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      ref={root}
      className="relative grid min-h-screen place-items-center overflow-hidden px-4 py-10"
    >
      <div
        className="blob blob-a"
        style={{
          width: 420,
          height: 420,
          left: -120,
          top: -80,
          opacity: 0.5,
          background:
            'radial-gradient(circle, var(--brand), transparent 70%)',
        }}
      />

      <div
        className="blob blob-b"
        style={{
          width: 380,
          height: 380,
          right: -80,
          bottom: -60,
          opacity: 0.35,
          background:
            'radial-gradient(circle, var(--mint), transparent 70%)',
        }}
      />

      <div className="relative w-full max-w-md">
        <div className="reveal mb-6 flex items-center gap-2 text-2xl font-extrabold">
          <i
            className="inline-block h-7 w-7 rounded-lg"
            style={{
              background:
                'linear-gradient(135deg, var(--brand), var(--mint))',
            }}
          />
          BrandSure
        </div>

        <h1 className="reveal mb-2 text-3xl font-extrabold">
          Review content{' '}
          <span className="gradient-text">
            before the world does.
          </span>
        </h1>

        <p className="reveal mb-6 text-mut">
          Checks every draft against your approved guidelines and facts,
          explains each issue with its source, and leaves the final call
          to people.
        </p>

        {/* Demo area: show feedback while checking availability. */}
        {healthLoading ? (
          <div
            className="reveal card mb-4"
            aria-live="polite"
            aria-busy="true"
            style={{
              borderColor: 'var(--brand)',
              boxShadow: '0 20px 50px var(--shadow)',
            }}
          >
            <p className="text-lg font-extrabold">
              Preparing your demo…
            </p>
            <p className="mt-2 text-sm text-mut">
              Connecting to BrandSure. Demo access will appear when ready.
            </p>
            <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-soft">
              <div className="h-full w-1/3 animate-pulse rounded-full bg-[var(--brand)]" />
            </div>
          </div>
        ) : health?.demo_login ? (
          <div
            className="reveal card mb-4"
            style={{
              borderColor: 'var(--brand)',
              boxShadow: '0 20px 50px var(--shadow)',
            }}
          >
            <p className="text-lg font-extrabold">
              Try the demo in one click
            </p>

            <p className="mb-3 text-sm text-mut">
              No sign-up. Sample data is already loaded. You can switch
              role at any time from the top bar.
            </p>

            <div className="grid gap-2">
              {DEMO_ROLES.map(([role, title, description]) => (
                <button
                  key={role}
                  type="button"
                  disabled={busy}
                  onClick={() => demo(role)}
                  className="flex items-center justify-between gap-3 rounded-2xl border border-line bg-soft p-3 text-left transition-transform hover:-translate-y-0.5 disabled:opacity-60"
                >
                  <span>
                    <b className="block">{title}</b>
                    <span className="text-xs text-mut">
                      {description}
                    </span>
                  </span>

                  <span className="btn !px-4 !py-2">
                    {busy ? 'Please wait…' : 'Enter'}
                  </span>
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <form
          onSubmit={submit}
          className="reveal card space-y-4"
          style={{ boxShadow: '0 30px 70px var(--shadow)' }}
        >
          <div
            role="tablist"
            className="flex gap-1 rounded-xl bg-soft p-1"
          >
            {[
              ['login', 'Sign in'],
              ...(health?.registration
                ? [['register', 'Create organisation']]
                : []),
            ].map(([key, label]) => (
              <button
                type="button"
                role="tab"
                key={key}
                aria-selected={mode === key}
                onClick={() => setMode(key)}
                className="flex-1 rounded-lg px-3 py-2 text-sm font-semibold"
                style={{
                  background:
                    mode === key ? 'var(--card)' : 'transparent',
                }}
              >
                {label}
              </button>
            ))}
          </div>

          <ErrorBanner error={err} />

          {info && (
            <p role="status" className="text-sm t-ok">
              {info}
            </p>
          )}

          {mode === 'register' && (
            <>
              <div>
                <label className="label" htmlFor="org">
                  Organisation name
                </label>
                <input
                  id="org"
                  required
                  className="input"
                  value={f.organisation_name}
                  onChange={set('organisation_name')}
                  autoComplete="organization"
                />
              </div>

              <div>
                <label className="label" htmlFor="dn">
                  Your name
                </label>
                <input
                  id="dn"
                  required
                  className="input"
                  value={f.display_name}
                  onChange={set('display_name')}
                  autoComplete="name"
                />
              </div>
            </>
          )}

          <div>
            <label className="label" htmlFor="em">
              Email
            </label>
            <input
              id="em"
              type="email"
              required
              autoComplete="email"
              className="input"
              value={f.email}
              onChange={set('email')}
            />
          </div>

          <div>
            <label className="label" htmlFor="pw">
              Password
              {mode === 'register' && ' (8+ characters)'}
            </label>
            <input
              id="pw"
              type="password"
              required
              minLength={mode === 'register' ? 8 : 1}
              autoComplete={
                mode === 'login'
                  ? 'current-password'
                  : 'new-password'
              }
              className="input"
              value={f.password}
              onChange={set('password')}
            />
          </div>

          <Button
            type="submit"
            busy={busy}
            className="w-full"
          >
            {mode === 'login' ? 'Sign in' : 'Create organisation'}
          </Button>

          {mode === 'register' && (
            <p className="text-xs text-mut">
              You become the Brand Admin and can add creators and
              reviewers afterwards.
            </p>
          )}
        </form>

        {health && (
          <p className="reveal mt-4 text-xs text-mut">
            <b>AI disclosure:</b> {health.ai_notice}
          </p>
        )}
      </div>
    </div>
  )
}
