import { Navigate } from 'react-router-dom'
import { useRef } from 'react'
import { api } from '../../lib/apiClient.js'
import { useAuth } from '../../lib/auth.jsx'
import { useLoad } from '../../lib/useLoad.js'
import { useStagger } from '../../lib/motion.js'
import { ErrorBanner, PageHeader, Spinner, Tag } from '../../components/ui/index.jsx'

export default function Settings() {
  const { user } = useAuth()
  const { data, error, loading, reload } = useLoad(() => (user.role === 'admin' ? api('/integrations') : Promise.resolve({ integrations: [] })))
  const root = useRef(null)
  useStagger(root, '.rv', [data])
  if (user.role !== 'admin') return <Navigate to="/" replace />
  if (loading && !data) return <Spinner />
  if (error) return <ErrorBanner error={error} onRetry={reload} />
  return (
    <div ref={root}>
      <PageHeader title="Integrations" subtitle="Optional services. Add the values to backend/.env, restart the server and reload this page." />
      <div className="grid gap-4 md:grid-cols-2">
        {data.integrations.map((i) => (
          <section key={i.id} className="card rv">
            <div className="mb-2 flex items-center justify-between gap-2"><h2 className="font-bold">{i.name}</h2><Tag tone={i.configured ? 'ok' : 'medium'}>{i.configured ? 'On' : 'Not set up'}</Tag></div>
            <p className="text-sm text-mut">{i.note}</p>
            {i.env.length > 0 && <p className="mt-3 text-xs"><b>Settings:</b> {i.env.map((e) => <code key={e} className="mr-2 rounded bg-soft px-1.5 py-0.5">{e}</code>)}</p>}
          </section>))}
      </div>
      <p className="mt-6 text-sm text-mut">Step-by-step instructions are in <code>docs/INTEGRATIONS.md</code>. Secret values are never shown here.</p>
    </div>
  )
}
