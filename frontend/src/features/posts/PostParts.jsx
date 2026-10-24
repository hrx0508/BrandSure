import { useState } from 'react'
import { AUDIT_LABEL, fmtDate } from '../../lib/formatters.js'
import { api } from '../../lib/apiClient.js'
import { Button, Tag } from '../../components/ui/index.jsx'
import { segments } from '../../lib/usePost.js'

/** The draft text with clickable highlights. `findings` decides what is highlighted (creators only get flagged ones). */
export function DraftText({ text, findings, active, onPick }) {
  return (
    <div className="whitespace-pre-wrap text-base" style={{ lineHeight: 1.8 }}>
      {segments(text, findings).map((s, i) => s.f ? (
        <mark key={i} role="button" tabIndex={0} title={`${s.f.severity} severity`} className={`hl hl-${s.f.severity} ${active === s.f.id ? 'hl-active' : ''}`}
          onClick={() => onPick(s.f.id)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onPick(s.f.id) } }}>{s.t}</mark>
      ) : <span key={i}>{s.t}</span>)}
    </div>
  )
}

export function VersionBar({ versions, cur, onPick }) {
  return (
    <div className="my-4 flex flex-wrap items-center gap-2" role="tablist" aria-label="Versions">
      {versions.map((x) => (
        <button key={x.id} role="tab" aria-selected={x.version_number === cur} onClick={() => onPick(x.version_number)} className="btn-alt"
          style={x.version_number === cur ? { background: 'var(--brand)', color: 'var(--brand-ink)', borderColor: 'var(--brand)' } : undefined}>
          Version {x.version_number}{x.author_role === 'reviewer' ? ' (reviewer edit)' : ''}</button>))}
    </div>
  )
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div role="tablist" className="mb-3 inline-flex flex-wrap gap-1 rounded-xl bg-soft p-1">
      {tabs.map(([k, l]) => <button key={k} role="tab" aria-selected={value === k} onClick={() => onChange(k)} className="rounded-lg px-4 py-2 text-sm font-semibold" style={{ background: value === k ? 'var(--card)' : 'transparent' }}>{l}</button>)}
    </div>
  )
}

export function Activity({ events, comments, reviewId, canComment, onPosted }) {
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  async function post() { setBusy(true); try { await api(`/reviews/${reviewId}/comments`, { method: 'POST', body: { body: text } }); setText(''); onPosted() } finally { setBusy(false) } }
  return (
    <div className="space-y-5">
      <section aria-labelledby="hist-h"><h2 id="hist-h" className="mb-2 font-bold">History</h2>
        {events?.length ? (
          <ol className="space-y-2 text-sm">{events.map((e) => (
            <li key={e.id}><b>{AUDIT_LABEL[e.action] || e.action}</b>{e.metadata?.version && <> <Tag tone="low">v{e.metadata.version}</Tag></>} <span className="text-mut">by {e.display_name} · {fmtDate(e.created_at)}</span>
              {e.metadata?.reason && <p className="text-mut">Note: {e.metadata.reason}</p>}
              {e.metadata?.override && <p className="t-medium">Approved with open high-severity findings.</p>}</li>))}</ol>
        ) : <p className="text-sm text-mut">No history yet.</p>}</section>
      <section aria-labelledby="com-h" className="space-y-2"><h2 id="com-h" className="font-bold">Comments</h2>
        {comments.map((c) => <p key={c.id} className="text-sm"><b>{c.display_name}</b> <span className="text-mut">{fmtDate(c.created_at)}</span><br />{c.body}</p>)}
        {!comments.length && <p className="text-sm text-mut">No comments yet.</p>}
        {canComment && (<div className="space-y-2"><label className="label" htmlFor="cm">Add a comment</label>
          <textarea id="cm" rows={2} className="input" value={text} onChange={(e) => setText(e.target.value)} />
          <Button variant="alt" disabled={!text.trim()} busy={busy} onClick={post}>Post comment</Button></div>)}</section>
    </div>
  )
}
