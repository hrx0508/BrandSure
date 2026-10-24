import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { api } from '../../lib/apiClient.js'
import { useAuth } from '../../lib/auth.jsx'
import { useLoad } from '../../lib/useLoad.js'
import { ROLE_LABEL } from '../../lib/formatters.js'
import { Button, ErrorBanner, PageHeader, Spinner } from '../../components/ui/index.jsx'

export default function Team() {
  const { user } = useAuth()
  const { data, error, loading, reload } = useLoad(() => (user.role === 'admin' ? api('/users') : Promise.resolve({ users: [] })))
  const [f, setF] = useState({ display_name: '', email: '', password: '', role: 'creator' })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [ok, setOk] = useState('')
  if (user.role !== 'admin') return <Navigate to="/" replace />
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  async function add(e) {
    e.preventDefault(); setBusy(true); setErr(null); setOk('')
    try { await api('/users', { method: 'POST', body: f }); setOk(`Added ${f.display_name}.`); setF({ display_name: '', email: '', password: '', role: 'creator' }); reload() }
    catch (x) { setErr(x) } finally { setBusy(false) }
  }
  return (
    <>
      <PageHeader title="Team" subtitle="Add the creators and reviewers who work in your organisation." />
      <div className="grid gap-6 lg:grid-cols-2">
        <form onSubmit={add} className="card space-y-3">
          <h2 className="font-bold">Add a person</h2>
          <ErrorBanner error={err} />
          {ok && <p role="status" className="text-sm t-ok">{ok}</p>}
          <div><label className="label" htmlFor="tn">Name</label><input id="tn" required className="input" value={f.display_name} onChange={set('display_name')} /></div>
          <div><label className="label" htmlFor="te">Email</label><input id="te" type="email" required className="input" value={f.email} onChange={set('email')} /></div>
          <div><label className="label" htmlFor="tp">Temporary password (8+ characters)</label><input id="tp" type="password" required minLength={8} className="input" value={f.password} onChange={set('password')} /></div>
          <div><label className="label" htmlFor="tr">Role</label>
            <select id="tr" className="input" value={f.role} onChange={set('role')}>{Object.entries(ROLE_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></div>
          <Button type="submit" busy={busy}>Add person</Button>
        </form>
        <section className="card"><h2 className="mb-3 font-bold">People</h2>
          {loading && !data ? <Spinner /> : error ? <ErrorBanner error={error} onRetry={reload} /> : (
            <ul className="divide-y divide-line">{data.users.map((u) => (
              <li key={u.id} className="flex items-center justify-between py-2 text-sm"><span><b>{u.display_name}</b><br /><span className="text-mut">{u.email}</span></span><span className="chip">{ROLE_LABEL[u.role]}</span></li>))}</ul>)}
        </section>
      </div>
    </>
  )
}
