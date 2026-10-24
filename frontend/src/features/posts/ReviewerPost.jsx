import { useRef, useState } from 'react'
import { api } from '../../lib/apiClient.js'
import { useAuth } from '../../lib/auth.jsx'
import { usePost } from '../../lib/usePost.js'
import { statusLabel } from '../../lib/formatters.js'
import { reduced, useStagger } from '../../lib/motion.js'
import { Button, ErrorBanner, PageHeader, Spinner, StatusTag } from '../../components/ui/index.jsx'
import ProcessTracker from '../../components/ProcessTracker.jsx'
import ReviewerPanel from '../approvals/ReviewerPanel.jsx'
import FlagCard from './FlagCard.jsx'
import ImagePanel from './ImagePanel.jsx'
import { TriageCharts } from './PostCharts.jsx'
import { Activity, DraftText, Tabs, VersionBar } from './PostParts.jsx'
import ScanPanel from './ScanPanel.jsx'

/** The reviewer's screen: Start review (Brand Kit + AI checks), flag or dismiss each finding, suggest or edit, then decide. */
export default function ReviewerPost({ id }) {
  const { user } = useAuth()
  const { data, error, loading, reload, setVer, audit } = usePost(id)
  const [tab, setTab] = useState('draft')
  const [active, setActive] = useState(null)
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState(null)
  const [note, setNote] = useState('')
  const list = useRef(null)
  useStagger(list, '.rv', [data?.findings.length, data?.current_version])

  if (loading && !data) return <Spinner />
  if (error && !data) return <ErrorBanner error={error} onRetry={reload} />
  if (!data) return <Spinner />
  const { review, versions, current_version: cur, latest_version: latest, findings, images, comments } = data
  const v = versions.find((x) => x.version_number === cur)
  const isLatest = cur === latest
  const mine = isLatest && review.status === 'in_review' && review.created_by !== user.id && (!review.reviewer_id || review.reviewer_id === user.id)
  const started = !!v.analyzed_at
  const live = findings.filter((f) => f.status !== 'dismissed')
  const open = findings.filter((f) => f.status === 'open').length
  const flagged = findings.filter((f) => f.status === 'flagged').length
  const openHigh = findings.filter((f) => f.severity === 'high' && ['open', 'flagged'].includes(f.status)).length
  const suggestions = findings.filter((f) => f.origin === 'reviewer' && f.status === 'flagged').length

  async function run(label, fn) { setBusy(label); setErr(null); setNote(''); try { await fn() } catch (e) { setErr(e) } finally { setBusy('') } }
  const startReview = (rerun = false) => run('start', async () => {
    if (rerun && !window.confirm('Run the checks again? Your flag and dismiss choices on automatic findings will be reset. Your own suggestions are kept.')) return
    const minimum = new Promise((r) => setTimeout(r, reduced() ? 0 : 1800)) // lets the scan animation be seen
    const [r] = await Promise.all([api(`/reviews/${id}/start-review`, { method: 'POST', body: { rerun } }), minimum])
    if (r.analysis.ai_error) setNote(`AI analysis failed (${r.analysis.ai_error}). Brand Kit rule checks still ran.`)
    setActive(null); await reload()
  })
  const triage = (fid, action) => run('triage', async () => { await api(`/reviews/${id}/findings/${fid}/triage`, { method: 'POST', body: { action } }); await reload() })
  const flagAll = () => run('triage', async () => { await api(`/reviews/${id}/triage-all`, { method: 'POST' }); await reload() })
  const done = (msg) => { setNote(msg); setVer(null); reload() }

  return (
    <>
      <PageHeader title={review.title} subtitle={`From ${review.creator_name} · ${review.kit_name} v${review.kit_version_number} · version ${cur} of ${latest}`}>
        <StatusTag status={review.status} label={statusLabel(review.status, 'reviewer')} />
      </PageHeader>
      <ProcessTracker review={review} role="reviewer" userId={user.id} started={started} />
      <VersionBar versions={versions} cur={cur} onPick={(n) => { setVer(n); setActive(null) }} />
      {!isLatest && <p role="note" className="card mb-4 text-sm">You are viewing an earlier version (read-only).</p>}
      {mine === false && review.status === 'in_review' && review.reviewer_id && <p role="note" className="card mb-4 text-sm">This post was sent to {review.reviewer_name}. You can look, but only they can review it.</p>}
      <ErrorBanner error={err} />
      {note && <p role="status" className="mb-4 rounded-2xl border p-3 text-sm t-medium" style={{ borderColor: 'var(--warn)' }}>{note}</p>}

      {mine && !started && (
        <section className="card mb-4 text-center" style={{ borderColor: 'var(--brand)', boxShadow: '0 20px 50px var(--shadow)' }}>
          {busy === 'start' ? <ScanPanel text={v.content} /> : (<>
            <h2 className="text-xl font-extrabold">Ready to review?</h2>
            <p className="mx-auto mt-1 max-w-xl text-sm text-mut">BrandSure will check this post against the Brand Kit{images.length ? ', including its images,' : ''} and AI where it is switched on. You then decide which findings are real problems and which are not.</p>
            <Button className="mt-4" onClick={() => startReview(false)}>Start review</Button></>)}
        </section>)}

      {started && <div className="mb-4"><TriageCharts findings={findings} /></div>}

      <div className="grid gap-6 lg:grid-cols-[1fr_26rem]">
        <section className="space-y-4" aria-label="Post under review">
          {mine && <ReviewerPanel key={`${id}-${cur}-${started}`} reviewId={id} versionNumber={cur} content={v.content} started={started} openHigh={openHigh} flagged={flagged} untriaged={open} suggestionCount={suggestions} creatorName={review.creator_name} onDone={done} />}
          <div className="card">
            <Tabs tabs={[['draft', 'Post'], ['images', `Images (${images.length})`], ['activity', 'Activity']]} value={tab} onChange={setTab} />
            {tab === 'draft' && (<><DraftText text={v.content} findings={live} active={active} onPick={setActive} />
              <p className="mt-3 text-xs text-mut">Highlights show findings that are not dismissed. Solid = high, dashed = medium, dotted = low.</p></>)}
            {tab === 'images' && (images.length ? <ImagePanel images={images} editable={false} reviewId={id} onChanged={() => {}} /> : <p className="text-sm text-mut">No images on this version.</p>)}
            {tab === 'activity' && <Activity events={audit.data?.events} comments={comments} reviewId={id} canComment onPosted={reload} />}
          </div>
        </section>

        <aside aria-labelledby="find-h">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 id="find-h" className="font-bold">Findings {started && `(${findings.length})`}</h2>
            {mine && started && <div className="flex gap-2">{open > 0 && <Button variant="alt" busy={busy === 'triage'} onClick={flagAll}>Flag all open ({open})</Button>}<Button variant="alt" onClick={() => startReview(true)}>Re-run</Button></div>}
          </div>
          {busy === 'start' && started ? <div className="card"><ScanPanel text={v.content} /></div>
            : !started ? <p className="card text-sm text-mut">{mine ? 'Press Start review to see what BrandSure finds.' : 'The review has not been started.'}</p>
            : !findings.length ? <p className="card text-sm">No issues detected by configured checks. This is not a guarantee of compliance.</p>
            : <ul ref={list} className="space-y-3">{findings.map((f) => (
              <FlagCard key={f.id} f={f} mode={mine ? 'reviewer' : 'view'} active={active === f.id} image={f.meta?.image_id ? images.find((i) => i.id === f.meta.image_id) : null}
                onSelect={() => setActive(active === f.id ? null : f.id)} onTriage={triage} />))}</ul>}
          {v.analysis && <p className="mt-3 text-xs text-mut">Checks: {v.analysis.ai_mode === 'llm' ? 'Brand Kit rules + AI' : v.analysis.ai_mode === 'offline_heuristic' ? 'Brand Kit rules (no external AI)' : 'Brand Kit rules (AI unavailable)'} · evaluated {v.analysis.evaluation_date}</p>}
        </aside>
      </div>
    </>
  )
}
