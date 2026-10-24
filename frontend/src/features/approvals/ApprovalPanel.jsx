import { useState } from 'react'
import { api } from '../../lib/apiClient.js'
import { Button, ErrorBanner } from '../../components/ui/index.jsx'

export default function ApprovalPanel({ reviewId, versionNumber, openHigh, onDone }) {
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  async function decide(decision) {
    if (decision === 'approve' && !window.confirm(`Approve version ${versionNumber}? This records you as the approver.`)) return
    setBusy(true); setErr(null)
    try { await api(`/reviews/${reviewId}/decision`, { method: 'POST', body: { decision, version_number: versionNumber, reason } }); onDone() }
    catch (e) { setErr(e) } finally { setBusy(false) }
  }
  return (
    <section className="card space-y-3" aria-labelledby="decision-h" style={{ boxShadow: '0 20px 50px var(--shadow)' }}>
      <h2 id="decision-h" className="text-lg font-bold">Your decision on version {versionNumber}</h2>
      {openHigh > 0 && <p className="text-sm t-medium">{openHigh} high-severity finding(s) are still open. Approving needs a reason.</p>}
      <ErrorBanner error={err} />
      <div><label className="label" htmlFor="reason">Reason or comment</label>
        <textarea id="reason" rows={3} className="input" value={reason} onChange={(e) => setReason(e.target.value)} /></div>
      <div className="flex flex-wrap gap-2">
        <Button busy={busy} onClick={() => decide('approve')}>Approve this version</Button>
        <Button busy={busy} variant="alt" onClick={() => decide('request_changes')}>Request changes</Button>
      </div>
      <p className="text-xs text-mut">Approval means a reviewer accepted this version. It does not guarantee every issue was detected.</p>
    </section>
  )
}
