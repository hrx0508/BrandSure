import { useState } from 'react'
import { useAuth } from '../../lib/auth.jsx'
import { usePost } from '../../lib/usePost.js'
import { statusLabel } from '../../lib/formatters.js'
import { ErrorBanner, PageHeader, Spinner, StatusTag } from '../../components/ui/index.jsx'
import ProcessTracker from '../../components/ProcessTracker.jsx'
import FlagCard from './FlagCard.jsx'
import { TriageCharts } from './PostCharts.jsx'
import { Activity, DraftText, Tabs, VersionBar } from './PostParts.jsx'

/** Admin: read-only view of any post, to see where it is and who it is waiting for. */
export default function AdminPost({ id }) {
  const { user } = useAuth()
  const { data, error, loading, reload, setVer, audit } = usePost(id)
  const [tab, setTab] = useState('draft')
  const [active, setActive] = useState(null)
  if (loading && !data) return <Spinner />
  if (error && !data) return <ErrorBanner error={error} onRetry={reload} />
  if (!data) return <Spinner />
  const { review, versions, current_version: cur, findings, comments } = data
  const v = versions.find((x) => x.version_number === cur)
  return (
    <>
      <PageHeader title={review.title} subtitle={`By ${review.creator_name} · ${review.kit_name} v${review.kit_version_number} · read only`}>
        <StatusTag status={review.status} label={statusLabel(review.status, 'admin')} />
      </PageHeader>
      <ProcessTracker review={review} role="admin" userId={user.id} started={!!v.analyzed_at} />
      <VersionBar versions={versions} cur={cur} onPick={(n) => { setVer(n); setActive(null) }} />
      {findings.length > 0 && <div className="mb-4"><TriageCharts findings={findings} /></div>}
      <div className="grid gap-6 lg:grid-cols-[1fr_26rem]">
        <div className="card">
          <Tabs tabs={[['draft', 'Post'], ['activity', 'Activity']]} value={tab} onChange={setTab} />
          {tab === 'draft' ? <DraftText text={v.content} findings={findings.filter((f) => f.status !== 'dismissed')} active={active} onPick={setActive} />
            : <Activity events={audit.data?.events} comments={comments} reviewId={id} canComment={false} onPosted={reload} />}
        </div>
        <aside><h2 className="mb-3 font-bold">Findings ({findings.length})</h2>
          {findings.length ? <ul className="space-y-3">{findings.map((f) => <FlagCard key={f.id} f={f} mode="view" active={active === f.id} onSelect={() => setActive(active === f.id ? null : f.id)} />)}</ul>
            : <p className="card text-sm text-mut">The reviewer has not started the review of this version.</p>}</aside>
      </div>
    </>
  )
}
