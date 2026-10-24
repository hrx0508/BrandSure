import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../lib/apiClient.js'
import { Button, ErrorBanner } from '../../components/ui/index.jsx'

/** Admin controls for one kit: send to creators, deactivate / activate, delete. */
export default function KitActions({ kit, onDone, onDeleted }) {
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState(null)
  async function act(name, path, method = 'POST', confirmText) {
    if (confirmText && !window.confirm(confirmText)) return
    setBusy(name); setErr(null)
    try { await api(`/brand-kits/${kit.id}${path}`, { method }); if (name === 'del' && onDeleted) onDeleted(); else onDone() } catch (e) { setErr(e) } finally { setBusy('') }
  }
  return (
    <div className="space-y-2">
      <ErrorBanner error={err} />
      <div className="flex flex-wrap gap-2">
        {kit.state === 'needs_confirmation' && <Link to={`/brand-kits/${kit.id}`} className="btn inline-block !py-2">Confirm the rules</Link>}
        {kit.state === 'ready_to_send' && <Button busy={busy === 'send'} onClick={() => act('send', '/publish')}>Send to creators</Button>}
        {kit.state === 'inactive'
          ? <Button variant="alt" busy={busy === 'on'} onClick={() => act('on', '/activate')}>Activate</Button>
          : <Button variant="alt" busy={busy === 'off'} onClick={() => act('off', '/deactivate', 'POST', 'Deactivate this Brand Kit? Creators will no longer be able to start posts with it. Posts already checked keep working.')}>Make inactive</Button>}
        <Button variant="alt" busy={busy === 'del'} onClick={() => act('del', '', 'DELETE', `Delete “${kit.name}” permanently? This cannot be undone.`)}>Delete</Button>
      </div>
    </div>
  )
}
