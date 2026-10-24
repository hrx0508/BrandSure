export function Button({ variant = 'primary', busy, children, className = '', ...p }) {
  const cls = variant === 'primary' ? 'btn' : variant === 'danger' ? 'btn btn-danger' : 'btn-alt'
  return <button {...p} disabled={p.disabled || busy} className={`${cls} ${className}`}>{busy ? 'Working…' : children}</button>
}
export const SEVERITY_TONE = { high: 'high', medium: 'medium', low: 'low' }
export function Tag({ tone = 'low', children }) { return <span className={`tag t-${tone}`}>{children}</span> }
export function SeverityTag({ severity }) { return <Tag tone={severity}>{severity[0].toUpperCase() + severity.slice(1)} severity</Tag> }
const STATUS_TONE = { approved: 'ok', published: 'ok', live: 'ok', in_review: 'brand', ready_to_send: 'brand', changes_requested: 'medium', needs_confirmation: 'medium', rejected: 'high', draft: 'low', inactive: 'low' }
export function StatusTag({ status, label }) { return <Tag tone={STATUS_TONE[status] || 'low'}>{label}</Tag> }
export function Spinner({ label = 'Loading…' }) { return <p role="status" className="text-sm text-mut py-8 text-center">{label}</p> }
export function ErrorBanner({ error, onRetry }) {
  if (!error) return null
  return (
    <div role="alert" className="mb-4 rounded-2xl border p-3 text-sm t-high" style={{ borderColor: 'var(--bad)', background: 'color-mix(in srgb, var(--bad) 10%, transparent)' }}>
      <strong>Error:</strong> {error.message}
      {error.requestId && <span className="text-mut"> (ref {error.requestId})</span>}
      {onRetry && <button onClick={onRetry} className="ml-3 underline">Try again</button>}
    </div>
  )
}
export function EmptyState({ title, children }) {
  return (
    <div className="card text-center py-12">
      <h2 className="text-lg font-bold">{title}</h2>
      <div className="mt-2 text-sm text-mut">{children}</div>
    </div>
  )
}
export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl md:text-4xl font-extrabold">{title}</h1>
        {subtitle && <p className="mt-1 text-mut">{subtitle}</p>}
      </div>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  )
}
/** Review lifecycle: Draft > Checked > In review > Approved. */
export function Stepper({ steps, current, warnAt }) {
  return (
    <ol className="flex items-center overflow-x-auto py-2" aria-label="Progress">
      {steps.map((s, i) => {
        const done = i < current || (i === current && current === steps.length - 1)
        const on = i <= current
        return (
          <li key={s} className="flex items-center" aria-current={i === current ? 'step' : undefined}>
            {i > 0 && <span className="mx-2 h-0.5 w-8 md:w-14" style={{ background: on ? 'var(--brand)' : 'var(--line)' }} />}
            <span className="flex items-center gap-2 text-sm font-semibold whitespace-nowrap" style={{ color: on ? 'var(--ink)' : 'var(--mut)' }}>
              <b className="grid h-8 w-8 place-items-center rounded-full border-2 text-xs"
                style={{ background: i === warnAt ? 'var(--warn)' : on ? 'var(--brand)' : 'var(--soft)', borderColor: i === warnAt ? 'var(--warn)' : on ? 'var(--brand)' : 'var(--line)', color: on ? 'var(--brand-ink)' : 'var(--mut)' }}>
                {done ? '✓' : i + 1}
              </b>
              {s}
            </span>
          </li>
        )
      })}
    </ol>
  )
}

export function ActorChip({ actor }) {
  const color = { Admin: 'var(--brand)', Creator: 'var(--mint)', Reviewer: 'var(--warn)' }[actor] || 'var(--mut)'
  return <span className="inline-flex items-center gap-1 text-xs font-semibold" style={{ color: 'var(--mut)' }}><i className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />{actor}</span>
}
