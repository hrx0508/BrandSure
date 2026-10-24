import { useState } from 'react'
import { api } from '../../lib/apiClient.js'
import { Button, ErrorBanner } from '../../components/ui/index.jsx'

const MODES = [['decide', 'Decide'], ['suggest', 'Suggest changes'], ['edit', 'Edit the post']]

/** Everything the reviewer can do to a post that was sent to them. */
export default function ReviewerPanel({ reviewId, versionNumber, content, started, openHigh, flagged, untriaged, suggestionCount, creatorName, onDone }) {
  const [mode, setMode] = useState('decide')
  const [reason, setReason] = useState('')
  const [sel, setSel] = useState({ start: 0, end: 0 })
  const [rep, setRep] = useState('')
  const [note, setNote] = useState('')
  const [edit, setEdit] = useState(content)
  const [editNote, setEditNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  async function call(path, body, message) {
    setBusy(true); setErr(null)
    try { await api(`/reviews/${reviewId}${path}`, { method: 'POST', body }); onDone(message) } catch (e) { setErr(e) } finally { setBusy(false) }
  }
  const decide = (decision) => {
    if (decision === 'approve' && !window.confirm(`Approve version ${versionNumber}? This records you as the approver.`)) return
    if (decision === 'reject' && !window.confirm('Reject this post? It will be closed and the creator will see your reason.')) return
    const msg = { approve: 'Approved. It is ready for the creator to publish.', request_changes: `Sent back to ${creatorName} with ${flagged} flagged item(s).`, reject: 'Post rejected.' }[decision]
    call('/decision', { decision, version_number: versionNumber, reason }, msg)
  }
  const selected = content.slice(sel.start, sel.end)
  return (
    <section className="card space-y-4" aria-labelledby="rp-h" style={{ borderColor: 'var(--brand)', boxShadow: '0 20px 50px var(--shadow)' }}>
      <h2 id="rp-h" className="text-lg font-bold">Your review of version {versionNumber}</h2>
      <div role="tablist" className="inline-flex flex-wrap gap-1 rounded-xl bg-soft p-1">
        {MODES.map(([k, l]) => <button key={k} role="tab" aria-selected={mode === k} onClick={() => setMode(k)} className="rounded-lg px-3 py-2 text-sm font-semibold" style={{ background: mode === k ? 'var(--card)' : 'transparent' }}>{l}{k === 'suggest' && suggestionCount ? ` (${suggestionCount})` : ''}</button>)}
      </div>
      <ErrorBanner error={err} />

      {mode === 'decide' && (
        <div className="space-y-3">
          <p className="text-sm text-mut">{started ? <><b>{flagged}</b> flagged for {creatorName}{untriaged > 0 && <>, <b>{untriaged}</b> not triaged yet</>}. {suggestionCount > 0 && `Includes ${suggestionCount} of your suggestion(s). `}</> : 'Press Start review first. You cannot approve a post that has not been checked against the Brand Kit.'}</p>
          {openHigh > 0 && <p className="text-sm t-medium">{openHigh} high-severity finding(s) are still open or flagged. Approving anyway needs a reason.</p>}
          <div><label className="label" htmlFor="reason">Reason or note for {creatorName}</label>
            <textarea id="reason" rows={3} className="input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Required to send back or reject" /></div>
          <div className="flex flex-wrap gap-2">
            <Button busy={busy} disabled={!started} onClick={() => decide('approve')}>Approve</Button>
            <Button busy={busy} variant="alt" onClick={() => decide('request_changes')}>Send back with flags</Button>
            <Button busy={busy} variant="danger" onClick={() => decide('reject')}>Reject</Button>
          </div>
          <p className="text-xs text-mut">Approval means you accepted this version. It does not guarantee every issue was detected.</p>
        </div>)}

      {mode === 'suggest' && (
        <div className="space-y-3">
          <p className="text-sm text-mut">Select the words you want changed, then write the replacement. It goes straight to the creator as a flag.</p>
          <label className="sr-only" htmlFor="sel">Draft text (select part of it)</label>
          <textarea id="sel" readOnly rows={6} className="input !text-base leading-relaxed" value={content}
            onSelect={(e) => { setSel({ start: e.target.selectionStart, end: e.target.selectionEnd }); if (e.target.selectionEnd > e.target.selectionStart) setRep(content.slice(e.target.selectionStart, e.target.selectionEnd)) }} />
          <p className="text-sm">{selected ? <>Selected: <b>“{selected}”</b></> : <span className="text-mut">Nothing selected yet.</span>}</p>
          <div className="grid gap-3 md:grid-cols-2">
            <div><label className="label" htmlFor="rep">Replace it with</label><input id="rep" className="input" value={rep} onChange={(e) => setRep(e.target.value)} /></div>
            <div><label className="label" htmlFor="sn">Note for {creatorName}</label><input id="sn" className="input" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Why this change?" /></div>
          </div>
          <Button busy={busy} disabled={!selected || !note.trim()} onClick={() => call('/suggestions', { version_number: versionNumber, start: sel.start, end: sel.end, replacement: rep, note }, 'Suggestion added. Send the post back when you are done.')}>Add suggestion</Button>
        </div>)}

      {mode === 'edit' && (
        <div className="space-y-3">
          <p className="text-sm text-mut">Edit the post yourself. It is saved as a new version marked as yours and goes back to {creatorName} to check and resend.</p>
          <label className="sr-only" htmlFor="ed">Edited post</label>
          <textarea id="ed" rows={8} className="input !text-base leading-relaxed" value={edit} onChange={(e) => setEdit(e.target.value)} />
          <div><label className="label" htmlFor="en">What did you change and why?</label><input id="en" className="input" value={editNote} onChange={(e) => setEditNote(e.target.value)} /></div>
          <Button busy={busy} disabled={!editNote.trim() || !edit.trim() || edit === content} onClick={() => call('/reviewer-edit', { content: edit, version_number: versionNumber, note: editNote }, `Your edit was saved and sent back to ${creatorName}.`)}>Save edit and send back</Button>
        </div>)}
    </section>
  )
}
