import { useRef } from 'react'
import { api } from '../../lib/apiClient.js'
import { useLoad } from '../../lib/useLoad.js'
import { STATUS_LABEL, TYPE_LABEL } from '../../lib/formatters.js'
import { useBars, useStagger } from '../../lib/motion.js'
import { BarList, Donut, LineChart } from '../../components/charts/Charts.jsx'
import { EmptyState, ErrorBanner, PageHeader, Spinner, Tag } from '../../components/ui/index.jsx'

const DECISION = { approve: 'Approved', request_changes: 'Sent back', reject: 'Rejected', edited: 'Reviewer edits' }

export default function Insights() {
  const { data, error, loading, reload } = useLoad(() => api('/insights'))
  const root = useRef(null)
  useBars(root, [data])
  useStagger(root, '.rv', [data])
  if (loading && !data) return <Spinner />
  if (error) return <ErrorBanner error={error} onRetry={reload} />
  if (data.insufficient_data) {
    return (<><PageHeader title="Insights" /><EmptyState title="Not enough data yet">Insights are built only from real review activity. Once reviewers start reviewing posts, charts appear here.</EmptyState></>)
  }
  const r = data.reviews
  const stat = [['Versions reviewed', data.versions_analyzed], ['Avg. hours to decision', r.avg_hours_to_decision ?? '–'], ['Avg. rounds to approval', data.avg_rounds ?? '–'],
    ['Sent-back rate', r.changes_requested_rate == null ? '–' : `${Math.round(r.changes_requested_rate * 100)}%`]]
  const statuses = Object.keys(STATUS_LABEL).map((k) => ({ label: STATUS_LABEL[k], value: r.counts[k] || 0 }))
  const decisions = Object.entries(data.decisions).map(([k, v]) => ({ label: DECISION[k] || k, value: v }))
  return (
    <div ref={root}>
      <PageHeader title="Insights" subtitle="Repeated mistakes, review progress and guideline areas that may be unclear. Built from real events only." />
      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {stat.map(([l, v]) => <div key={l} className="card rv"><p className="text-3xl font-extrabold">{v}</p><p className="text-sm text-mut">{l}</p></div>)}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="card rv"><h2 className="mb-4 font-bold">Issues by category</h2>
          <Donut centerLabel="issues" data={data.by_type.map((t) => ({ label: TYPE_LABEL[t.type] || t.type, value: t.count }))} /></section>
        <section className="card rv"><h2 className="mb-4 font-bold">Activity by day</h2>
          <LineChart aLabel="Versions reviewed" bLabel="Findings" points={data.timeline.map((d) => ({ label: d.date, a: d.versions, b: d.findings }))} /></section>
        <section className="card rv"><h2 className="mb-4 font-bold">Where posts are now</h2><BarList items={statuses} /></section>
        <section className="card rv"><h2 className="mb-4 font-bold">Reviewer decisions</h2>
          {decisions.length ? <Donut centerLabel="decisions" data={decisions} /> : <p className="text-sm text-mut">No decisions yet.</p>}</section>
        <section className="card rv lg:col-span-2"><h2 className="mb-1 font-bold">Rules reviewers dismiss most</h2>
          <p className="mb-3 text-xs text-mut">When reviewers dismiss a finding as “not an issue” in half or more of a rule’s appearances (at least 3), the rule may be unclear or too strict. Consider rewording it in the Brand Kit.</p>
          <ul className="grid gap-4 md:grid-cols-2">{data.rules.slice(0, 8).map((x) => (
            <li key={x.title} className="text-sm">
              <div className="flex items-center justify-between gap-2"><span className="font-semibold">{x.title}</span>
                {x.possibly_unclear ? <Tag tone="medium">Possibly unclear</Tag> : x.dismiss_rate == null ? <span className="text-xs text-mut">Too few observations</span> : null}</div>
              <div className="mt-1 grid grid-cols-[1fr_3rem] items-center gap-3"><div className="bar"><i data-w={Math.round((x.dismiss_rate || 0) * 100)} /></div>
                <span className="text-xs text-mut">{x.dismiss_rate == null ? '–' : `${Math.round(x.dismiss_rate * 100)}%`}</span></div>
              <p className="text-xs text-mut">Found {x.shown}× · flagged {x.flagged}× · dismissed {x.dismissed}×</p></li>))}</ul></section>
      </div>
    </div>
  )
}
