import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../lib/apiClient.js'
import { useAuth } from '../../lib/auth.jsx'
import { fmtDate, statusLabel, TYPE_LABEL } from '../../lib/formatters.js'
import { useLoad } from '../../lib/useLoad.js'
import { gsap, reduced, useStagger } from '../../lib/motion.js'
import { ErrorBanner, Spinner, StatusTag } from '../../components/ui/index.jsx'
import { BarList, Donut, Ring } from '../../components/charts/Charts.jsx'
import TaskPanel from './TaskPanel.jsx'

const WORDS = ['logos', 'claims', 'facts', 'tone', 'contrast', 'alt text']
const CHIPS = ['Audit trail', 'Tone of voice', 'Unsupported claims', 'Outdated facts', 'Banned terms', 'Logo usage', 'Colour palette', 'Alt text', 'Contrast', 'Approvals']

function Count({ to }) {
  const ref = useRef(null)
  useEffect(() => {
    if (!ref.current) return undefined
    if (reduced()) { ref.current.textContent = String(to); return undefined }
    const o = { v: 0 }
    const tw = gsap.to(o, { v: to, duration: 0.9, ease: 'power2.out', onUpdate: () => { if (ref.current) ref.current.textContent = String(Math.round(o.v)) } })
    return () => tw.kill()
  }, [to])
  return <span ref={ref}>0</span>
}

export default function Home() {
  const { user } = useAuth()
  const ov = useLoad(() => api('/overview'))
  const tasks = useLoad(() => api('/tasks'))
  const fb = useLoad(() => (user.role === 'creator' ? api('/my-feedback') : Promise.resolve(null)))
  const hero = useRef(null)
  const grid = useRef(null)
  const word = useRef(null)

  useEffect(() => {
    if (reduced() || !hero.current) return undefined
    let i = 0
    const swap = () => {
      gsap.to(word.current, { y: -14, opacity: 0, duration: 0.25, onComplete: () => {
        i = (i + 1) % WORDS.length
        if (word.current) { word.current.textContent = WORDS[i]; gsap.fromTo(word.current, { y: 14, opacity: 0 }, { y: 0, opacity: 1, duration: 0.3 }) }
      } })
    }
    const id = setInterval(swap, 2400)
    const ctx = gsap.context(() => {
      gsap.from('.h-in', { y: 28, opacity: 0, stagger: 0.12, duration: 0.7, ease: 'power3.out' })
      gsap.to('.hb1', { x: 30, y: 20, duration: 6, yoyo: true, repeat: -1, ease: 'sine.inOut' })
      gsap.to('.hb2', { x: -40, y: -10, duration: 7, yoyo: true, repeat: -1, ease: 'sine.inOut' })
    }, hero)
    return () => { clearInterval(id); ctx.revert() }
  }, [])
  useStagger(grid, '.rv', [ov.data])

  if ((ov.loading && !ov.data) || (tasks.loading && !tasks.data) || (fb.loading && user.role === 'creator' && !fb.data)) return <Spinner />
  if (ov.error || tasks.error) return <ErrorBanner error={ov.error || tasks.error} onRetry={() => { ov.reload(); tasks.reload() }} />
  const { counts, recent, active_kits: kits } = ov.data
  const next = {
    admin: kits === 0 ? ['Upload your brand guidelines to create the first Brand Kit.', '/brand-kits', 'Upload guidelines'] : ['Your Brand Kit is live. See how the team is doing.', '/insights', 'Open insights'],
    creator: kits === 0 ? ['Waiting for the admin to send you a Brand Kit.', '/brand-kits', 'See Brand rules'] : ['Write your post and submit it. Your reviewer flags anything that needs fixing.', '/posts/new', 'Create post'],
    reviewer: (counts.in_review || 0) > 0 ? [`${counts.in_review} post(s) are waiting for your review.`, '/posts', 'Open review queue'] : ['Nothing is waiting for you right now.', '/posts', 'Open review queue'],
  }[user.role]
  const STATS = {
    admin: [['Live Brand Kits', kits], ['With creators', (counts.draft || 0) + (counts.changes_requested || 0)], ['With reviewers', counts.in_review || 0], ['Approved or published', (counts.approved || 0) + (counts.published || 0)]],
    creator: [['My drafts', counts.draft || 0], ['Submitted', counts.in_review || 0], ['Sent back to fix', counts.changes_requested || 0], ['Approved or published', (counts.approved || 0) + (counts.published || 0)]],
    reviewer: [['To review', counts.in_review || 0], ['Sent back to creators', counts.changes_requested || 0], ['Approved', (counts.approved || 0) + (counts.published || 0)], ['Rejected', counts.rejected || 0]],
  }[user.role]

  return (
    <>
      <section ref={hero} className="relative -mx-4 mb-8 overflow-hidden rounded-3xl px-6 py-14 md:px-12">
        <div className="blob hb1" style={{ width: 380, height: 380, left: -120, top: -80, opacity: 0.5, background: 'radial-gradient(circle, var(--brand), transparent 70%)' }} />
        <div className="blob hb2" style={{ width: 340, height: 340, right: -60, top: 20, opacity: 0.35, background: 'radial-gradient(circle, var(--mint), transparent 70%)' }} />
        <div className="relative max-w-2xl">
          <h1 className="h-in text-4xl font-extrabold leading-tight md:text-6xl">
            Catch off-brand <span ref={word} className="inline-block text-brand" style={{ borderBottom: '4px solid var(--mint)' }}>logos</span> before they go live.
          </h1>
          <p className="h-in mt-5 text-lg text-mut">Checks every draft against your approved guidelines and facts, explains each issue with its source, and leaves the final call to people.</p>
          <div className="h-in mt-7 flex flex-wrap items-center gap-4">
            <Link to={next[1]} className="btn inline-block">{next[2]}</Link>
            <span className="text-sm text-mut">{next[0]}</span>
          </div>
        </div>
      </section>
      <div className="marquee mb-8" aria-hidden="true"><div>{[...CHIPS, ...CHIPS].map((c, i) => <span key={i} className="chip whitespace-nowrap px-4 py-2 text-sm">{c}</span>)}</div></div>

      <div ref={grid}>
        <h2 className="mb-3 text-xl font-bold rv">What needs you</h2>
        <div className="rv"><TaskPanel tasks={tasks.data} role={user.role} /></div>
        <div className="my-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {STATS.map(([l, n]) => (
            <div key={l} className="card rv"><p className="text-4xl font-extrabold"><Count to={n} /></p><p className="text-sm text-mut">{l}</p></div>
          ))}
        </div>
        {user.role === 'creator' && fb.data && (fb.data.open + fb.data.fixed) > 0 && (
          <section className="card rv mb-4" aria-label="Red flags across your posts"><h2 className="mb-4 font-bold">Red flags from your reviewers</h2>
            <div className="grid items-center gap-6 md:grid-cols-3">
              <div><Ring value={fb.data.fixed} total={fb.data.open + fb.data.fixed} label="fixed" /><p className="mt-2 text-xs text-mut">{fb.data.open} still need your fix</p></div>
              <Donut size={130} centerLabel="flags" data={Object.entries(fb.data.by_type).map(([k, v]) => ({ label: TYPE_LABEL[k] || k, value: v }))} />
              <BarList items={fb.data.posts.filter((p) => p.open + p.fixed > 0).map((p) => ({ label: p.title.slice(0, 22), value: p.open, hint: `${p.open} to fix, ${p.fixed} fixed` }))} />
            </div></section>)}
        <div className="grid gap-4 lg:grid-cols-2">
          <section className="card rv"><h2 className="mb-3 font-bold">Where {user.role === 'creator' ? 'your' : 'the'} posts are</h2>
            <BarList items={['draft', 'in_review', 'changes_requested', 'approved', 'published', 'rejected'].map((k) => ({ label: statusLabel(k, user.role), value: counts[k] || 0 }))} /></section>
          <section className="card rv"><h2 className="mb-3 font-bold">Recent posts</h2>
            {!recent.length ? <p className="text-sm text-mut">No posts yet. They appear here once a creator starts one.</p> : (
              <ul className="space-y-2">{recent.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center justify-between gap-2">
                  <Link to={`/posts/${r.id}`} className="text-sm font-semibold text-brand hover:underline">{r.title}</Link>
                  <span className="flex items-center gap-2"><span className="text-xs text-mut">{fmtDate(r.updated_at)}</span><StatusTag status={r.status} label={statusLabel(r.status, user.role)} /></span>
                </li>))}</ul>)}
            <Link to="/guide" className="mt-4 inline-block text-sm font-semibold text-brand underline">See who does what</Link>
          </section>
        </div>
      </div>
    </>
  )
}
