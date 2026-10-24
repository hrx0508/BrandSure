import { useRef } from 'react'
import { Link } from 'react-router-dom'
import { fmtDate } from '../../lib/formatters.js'
import { useStagger } from '../../lib/motion.js'

function List({ title, items, tone, empty }) {
  return (
    <section className="card" style={tone === 'todo' && items.length ? { borderColor: 'var(--brand)', boxShadow: '0 12px 34px var(--shadow)' } : undefined} aria-label={title}>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-bold">{title}</h2>
        <span className="chip" style={tone === 'todo' && items.length ? { background: 'var(--brand)', color: 'var(--brand-ink)', borderColor: 'var(--brand)' } : undefined}>{items.length}</span>
      </div>
      {!items.length ? <p className="text-sm text-mut">{empty}</p> : (
        <ul className="space-y-2">
          {items.map((t, i) => (
            <li key={`${t.kind}-${i}`} className="tk">
              <Link to={t.link} className="block rounded-xl border border-line p-3 transition-colors hover:bg-soft">
                <p className="text-sm font-semibold">{t.title}</p>
                <p className="text-xs text-mut">{t.detail}{t.at ? ` · ${fmtDate(t.at)}` : ''}</p>
              </Link>
            </li>))}
        </ul>)}
    </section>
  )
}

/** The person's own to-do list and what they are waiting for from others (different for every role). */
export default function TaskPanel({ tasks, role }) {
  const ref = useRef(null)
  useStagger(ref, '.tk', [tasks])
  const waitingTitle = { admin: 'Waiting on others', creator: 'Waiting for the reviewer', reviewer: 'Waiting for creators' }[role]
  return (
    <div ref={ref} className="grid gap-4 md:grid-cols-2">
      <List title="Your to-do" items={tasks.todo} tone="todo" empty="You are all caught up. Nothing needs your action right now." />
      <List title={waitingTitle} items={tasks.waiting} tone="wait" empty="You are not waiting for anyone." />
    </div>
  )
}
