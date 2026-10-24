import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../lib/apiClient.js'
import { useAuth } from '../../lib/auth.jsx'
import { useLoad } from '../../lib/useLoad.js'
import { applyChanges, usePost } from '../../lib/usePost.js'
import { statusLabel } from '../../lib/formatters.js'
import { useStagger } from '../../lib/motion.js'
import { Button, ErrorBanner, PageHeader, Spinner, StatusTag } from '../../components/ui/index.jsx'
import ProcessTracker from '../../components/ProcessTracker.jsx'
import FlagCard from './FlagCard.jsx'
import ImagePanel from './ImagePanel.jsx'
import { FlagCharts } from './PostCharts.jsx'
import { Activity, DraftText, Tabs, VersionBar } from './PostParts.jsx'

/** The creator's screen: write the post, submit it, then see ONLY what the reviewer flagged and fix it. No checking tools here. */
export default function CreatorPost({ id }) {
  const { user } = useAuth()
  const { data, error, loading, reload, setVer, audit } = usePost(id)
  const reviewers = useLoad(() => api('/reviewers'))
  const health = useLoad(() => api('/health'))
  const [tab, setTab] = useState('draft')
  const [active, setActive] = useState(null)
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState(null)
  const [note, setNote] = useState('')
  const [editText, setEditText] = useState(null)
  const [pick, setPick] = useState(null)
  const list = useRef(null)
  useStagger(list, '.rv', [data?.findings.length, data?.current_version])

  if (loading && !data) return <Spinner />
  if (error && !data) return <ErrorBanner error={error} onRetry={reload} />
  if (!data) return <Spinner />
  const { review, versions, current_version: cur, latest_version: latest, findings: flags, images, decisions, comments } = data
  const v = versions.find((x) => x.version_number === cur)
  const isLatest = cur === latest
  const editable = review.created_by === user.id && isLatest && ['draft', 'changes_requested'].includes(review.status)
  const pending = applyChanges(v.content, flags)
  const stillFlagged = flags.filter((f) => f.status === 'flagged').length
  const reviewerChoice = pick ?? review.reviewer_id ?? ''
  const last = decisions[decisions.length - 1]

  async function run(label, fn) { setBusy(label); setErr(null); setNote(''); try { await fn() } catch (e) { setErr(e) } finally { setBusy('') } }
  const updateFlag = (fid, status, final_text) => run('flag', async () => { await api(`/reviews/${id}/findings/${fid}`, { method: 'POST', body: { status, final_text } }); await reload() })
  const saveVersion = (content) => run('save', async () => {
    await api(`/reviews/${id}/revisions`, { method: 'POST', body: { content } }); setVer(null); setActive(null); setEditText(null); setNote('Saved as a new version. Resubmit when you are done.'); await reload()
  })
  const submit = () => run('submit', async () => {
    await api(`/reviews/${id}/request-review`, { method: 'POST', body: { reviewer_id: reviewerChoice || null } })
    setNote('Submitted. Your reviewer will check it against the Brand Kit and flag anything that needs fixing.'); await reload()
  })
  const publish = () => run('publish', async () => { await api(`/reviews/${id}/mark-published`, { method: 'POST' }); await reload() })
  const changed = (msg) => { setNote(msg); reload() }

  return (
    <>
      <PageHeader title={review.title} subtitle={`Your post · ${review.kit_name} v${review.kit_version_number} · version ${cur} of ${latest}`}>
        <StatusTag status={review.status} label={statusLabel(review.status, 'creator')} />
      </PageHeader>
      <ProcessTracker review={review} role="creator" userId={user.id} />

      {review.status === 'changes_requested' && last && (
        <div role="note" className="card mt-4" style={{ borderColor: 'var(--warn)' }}>
          <p className="font-bold t-medium">{last.display_name} {last.decision === 'edited' ? 'edited your post' : 'sent this back'}</p>
          <p className="text-sm">{last.reason}</p>
        </div>)}
      {review.status === 'rejected' && last && <div role="note" className="card mt-4" style={{ borderColor: 'var(--bad)' }}><p className="font-bold t-high">Rejected by {last.display_name}</p><p className="text-sm">{last.reason}</p><Link to="/posts/new" className="mt-2 inline-block text-sm font-semibold text-brand underline">Create a new post</Link></div>}

      <VersionBar versions={versions} cur={cur} onPick={(n) => { setVer(n); setActive(null); setEditText(null) }} />
      {!isLatest && <p role="note" className="card mb-4 text-sm">You are viewing an earlier version (read-only). Earlier versions are always kept.</p>}
      <ErrorBanner error={err} />
      {note && <p role="status" className="mb-4 rounded-2xl border p-3 text-sm t-medium" style={{ borderColor: 'var(--warn)' }}>{note}</p>}
      {flags.length > 0 && <div className="mb-4"><FlagCharts flags={flags} /></div>}

      <div className="grid gap-6 lg:grid-cols-[1fr_26rem]">
        <section className="space-y-4" aria-label="Your post">
          <div className="card">
            <Tabs tabs={[['draft', 'Post'], ['images', `Images (${images.length})`], ['activity', 'Activity']]} value={tab} onChange={setTab} />
            {tab === 'draft' && (editText != null ? (
              <div className="space-y-2">
                <label className="sr-only" htmlFor="edit-draft">Edit post</label>
                <textarea id="edit-draft" rows={10} className="input !text-base leading-relaxed" value={editText} onChange={(e) => setEditText(e.target.value)} />
                <div className="flex gap-2"><Button busy={busy === 'save'} disabled={!editText.trim() || editText === v.content} onClick={() => saveVersion(editText)}>Save as version {latest + 1}</Button><Button variant="alt" onClick={() => setEditText(null)}>Cancel</Button></div>
              </div>
            ) : (<>
              <DraftText text={v.content} findings={flags} active={active} onPick={setActive} />
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs text-mut">{flags.length ? 'Highlights are what your reviewer flagged. Solid = high, dashed = medium, dotted = low.' : 'Nothing is flagged on this version.'}</p>
                {editable && <button className="btn-alt" onClick={() => setEditText(v.content)}>Edit post</button>}
              </div></>))}
            {tab === 'images' && <ImagePanel images={images} editable={editable} reviewId={id} onChanged={changed} aiEnabled={!!health.data?.ai_enabled} />}
            {tab === 'activity' && <Activity events={audit.data?.events} comments={comments} reviewId={id} canComment onPosted={reload} />}
          </div>

          {editable && (
            <div className="card space-y-3" style={{ borderColor: 'var(--brand)' }}>
              <h2 className="font-bold">Your next step</h2>
              {review.status === 'draft'
                ? <p className="text-sm text-mut">Finish your post and attach any images. When it is ready, submit it. The reviewer checks it against the Brand Kit and flags anything that needs fixing.</p>
                : <p className="text-sm text-mut">{stillFlagged ? `${stillFlagged} flagged item(s) still need a fix. ` : 'All flagged items are handled. '}Accept suggestions or edit the text, save your corrections, then resubmit.</p>}
              <div className="flex flex-wrap items-end gap-3">
                {pending.used.length > 0 && <Button busy={busy === 'save'} onClick={() => saveVersion(pending.text)}>Save {pending.used.length} correction(s) as version {latest + 1}</Button>}
                <div><label className="label" htmlFor="rv">Submit to</label>
                  <select id="rv" className="input" value={reviewerChoice} onChange={(e) => setPick(e.target.value)}>
                    <option value="">Any reviewer</option>{(reviewers.data?.reviewers || []).map((r) => <option key={r.id} value={r.id}>{r.display_name}</option>)}</select></div>
                <Button busy={busy === 'submit'} variant={pending.used.length ? 'alt' : 'primary'} disabled={pending.used.length > 0} onClick={submit}>{review.status === 'draft' ? 'Submit to reviewer' : 'Resubmit to reviewer'}</Button>
              </div>
              {pending.used.length > 0 && <ul className="text-sm">{pending.used.map((f) => <li key={f.id}><span className="line-through text-mut">{f.quoted_text}</span> → <b>{f.final_text ?? f.replacement}</b></li>)}<li className="mt-1 text-xs text-mut">Save these first, then resubmit.</li></ul>}
            </div>)}
          {review.status === 'approved' && review.created_by === user.id && (
            <div className="card space-y-3" style={{ borderColor: 'var(--ok)' }}><h2 className="font-bold">Approved</h2>
              <p className="text-sm text-mut">Version {latest} was approved. Publish it where it belongs, then record it here.</p>
              <Button busy={busy === 'publish'} onClick={publish}>Mark as published</Button></div>)}
        </section>

        <aside aria-labelledby="flag-h">
          <h2 id="flag-h" className="mb-3 font-bold">Flagged by your reviewer {flags.length > 0 && `(${stillFlagged} to fix of ${flags.length})`}</h2>
          {!flags.length ? (
            <p className="card text-sm text-mut">{review.status === 'draft' ? 'Nothing here yet. Submit your post and your reviewer will flag anything that needs fixing.' : review.status === 'in_review' ? 'Your reviewer is on it. Flags will appear here.' : 'Nothing was flagged on this version.'}</p>
          ) : (
            <ul ref={list} className="space-y-3">{flags.map((f) => (
              <FlagCard key={f.id} f={f} mode={editable ? 'creator' : 'view'} active={active === f.id} image={f.meta?.image_id ? images.find((i) => i.id === f.meta.image_id) : null}
                onSelect={() => setActive(active === f.id ? null : f.id)} onCreator={updateFlag} />))}</ul>)}
        </aside>
      </div>
    </>
  )
}
