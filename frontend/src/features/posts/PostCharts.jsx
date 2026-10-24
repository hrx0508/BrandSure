import { TYPE_LABEL } from '../../lib/formatters.js'
import { BarList, Donut, Ring, StackBar } from '../../components/charts/Charts.jsx'

const count = (items, key) => Object.entries(items.reduce((a, f) => ({ ...a, [f[key]]: (a[f[key]] || 0) + 1 }), {}))
const SEV = ['high', 'medium', 'low']

/** Creator: the red flags on this post, how many are fixed, and by what kind. */
export function FlagCharts({ flags }) {
  const fixed = flags.filter((f) => f.status !== 'flagged').length
  const sev = SEV.map((s) => ({ label: `${s[0].toUpperCase()}${s.slice(1)} severity`, value: flags.filter((f) => f.severity === s).length })).filter((x) => x.value)
  const types = count(flags, 'type').map(([k, v]) => ({ label: TYPE_LABEL[k] || k, value: v }))
  if (!flags.length) return null
  return (
    <section className="card rv" aria-label="Red flags overview">
      <h2 className="mb-4 font-bold">Red flags from your reviewer</h2>
      <div className="grid items-center gap-6 md:grid-cols-3">
        <div><Ring value={fixed} total={flags.length} label="fixed" /><p className="mt-2 text-xs text-mut">{flags.length - fixed} still need your fix</p></div>
        <Donut size={130} centerLabel="flags" data={sev} />
        <BarList items={types} />
      </div>
    </section>
  )
}

/** Reviewer: how the findings are being triaged. */
export function TriageCharts({ findings }) {
  const open = findings.filter((f) => f.status === 'open').length
  const flagged = findings.filter((f) => f.status === 'flagged').length
  const dismissed = findings.filter((f) => f.status === 'dismissed').length
  const live = findings.filter((f) => f.status !== 'dismissed')
  const sev = SEV.map((s) => ({ label: `${s[0].toUpperCase()}${s.slice(1)} severity`, value: live.filter((f) => f.severity === s).length })).filter((x) => x.value)
  const types = count(live, 'type').map(([k, v]) => ({ label: TYPE_LABEL[k] || k, value: v }))
  if (!findings.length) return null
  return (
    <section className="card rv" aria-label="Review overview">
      <h2 className="mb-4 font-bold">What BrandSure found</h2>
      <StackBar parts={[{ label: 'Not triaged', value: open }, { label: 'Flagged for creator', value: flagged }, { label: 'Dismissed', value: dismissed }]} />
      <div className="mt-5 grid items-center gap-6 md:grid-cols-2">
        {sev.length ? <Donut size={130} centerLabel="open + flagged" data={sev} /> : <p className="text-sm text-mut">Everything was dismissed.</p>}
        {types.length > 0 && <BarList items={types} />}
      </div>
    </section>
  )
}
