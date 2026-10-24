import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../lib/apiClient.js'
import { useAuth } from '../../lib/auth.jsx'
import { useLoad } from '../../lib/useLoad.js'
import { fmtDate, statusLabel } from '../../lib/formatters.js'
import { useStagger } from '../../lib/motion.js'
import { EmptyState, ErrorBanner, PageHeader, Spinner, StatusTag } from '../../components/ui/index.jsx'

const FILTERS = { creator: ['all', 'draft', 'in_review', 'changes_requested', 'approved', 'published', 'rejected'], reviewer: ['in_review', 'changes_requested', 'approved', 'rejected', 'all'], admin: ['all', 'in_review', 'changes_requested', 'draft', 'approved', 'published', 'rejected'] }
const TITLE = { creator: ['My posts', 'Everything you have written and what the reviewer said.'], reviewer: ['Review queue', 'Posts creators have submitted to you.'], admin: ['All posts', 'Where every post is and who it is waiting for.'] }

export default function PostsList() {
  const { user } = useAuth()
  const { data, error, loading, reload } = useLoad(() => api('/reviews'))
  const [filter, setFilter] = useState(FILTERS[user.role][0])
  const list = useRef(null)
  const rows = (data?.reviews || []).filter((r) => filter === 'all' || r.status === filter)
  useStagger(list, '.rv', [data, filter])
  const count = (s) => (data?.reviews || []).filter((r) => s === 'all' || r.status === s).length
  const label = (s) => (s === 'all' ? 'All' : statusLabel(s, user.role))
  return (
    <>
      <PageHeader title={TITLE[user.role][0]} subtitle={TITLE[user.role][1]}>
        {user.role === 'creator' && <Link to="/posts/new" className="btn inline-block">Create post</Link>}
      </PageHeader>
      <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Filter by status">
        {FILTERS[user.role].map((s) => (
          <button key={s} aria-pressed={filter === s} onClick={() => setFilter(s)} className="btn-alt"
            style={filter === s ? { background: 'var(--brand)', color: 'var(--brand-ink)', borderColor: 'var(--brand)' } : undefined}>{label(s)} ({count(s)})</button>))}
      </div>
      {loading && !data ? <Spinner /> : error ? <ErrorBanner error={error} onRetry={reload} /> : !rows.length ? (
        <EmptyState title="Nothing here">{user.role === 'creator' ? 'Create a post to get started.' : user.role === 'reviewer' ? 'No posts are waiting for you.' : 'No posts with this status.'}</EmptyState>
      ) : (
        <ul ref={list} className="grid gap-2">{rows.map((r) => (
          <li key={r.id} className="card rv flex flex-wrap items-center justify-between gap-2 !py-3">
            <span><Link to={`/posts/${r.id}`} className="font-semibold text-brand hover:underline">{r.title}</Link>
              <span className="block text-xs text-mut">{user.role !== 'creator' && `by ${r.creator_name} · `}{r.status === 'in_review' ? `with ${r.reviewer_name || 'any reviewer'}` : r.status === 'changes_requested' ? 'waiting for the creator' : ''}{r.round > 0 ? ` · round ${r.round}` : ''}</span></span>
            <span className="flex items-center gap-3"><span className="text-xs text-mut">{fmtDate(r.updated_at)}</span><StatusTag status={r.status} label={statusLabel(r.status, user.role)} /></span>
          </li>))}
        </ul>)}
    </>
  )
}
