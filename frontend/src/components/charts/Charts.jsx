import { useEffect, useRef } from 'react'
import { gsap, reduced } from '../../lib/motion.js'

export const PALETTE = ['var(--brand)', 'var(--mint)', 'var(--warn)', 'var(--bad)', '#4F9DFF', '#B26BFF', '#8A87A8']

/** Donut chart. data: [{ label, value }]. Includes a text legend so colour is never the only cue. */
export function Donut({ data, size = 170, centerLabel }) {
  const ref = useRef(null)
  const total = data.reduce((a, d) => a + d.value, 0) || 1
  const R = 60
  const C = 2 * Math.PI * R
  let offset = 0
  useEffect(() => {
    if (reduced() || !ref.current) return undefined
    const tw = gsap.fromTo(ref.current.querySelectorAll('circle.seg'), { opacity: 0, scale: 0.9, transformOrigin: '80px 80px' }, { opacity: 1, scale: 1, stagger: 0.1, duration: 0.6, ease: 'power2.out' })
    return () => tw.kill()
  }, [data])
  return (
    <div ref={ref} className="flex flex-wrap items-center gap-6">
      <svg width={size} height={size} viewBox="0 0 160 160" role="img" aria-label={`Chart: ${data.map((d) => `${d.label} ${d.value}`).join(', ')}`}>
        <circle cx="80" cy="80" r={R} fill="none" stroke="var(--soft)" strokeWidth="22" />
        <g transform="rotate(-90 80 80)">
          {data.map((d, i) => {
            const len = (d.value / total) * C
            const el = <circle key={d.label} className="seg" cx="80" cy="80" r={R} fill="none" stroke={PALETTE[i % PALETTE.length]} strokeWidth="22" strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-offset} />
            offset += len
            return el
          })}
        </g>
        <text x="80" y="78" textAnchor="middle" fontSize="26" fontWeight="800" fill="var(--ink)">{total}</text>
        <text x="80" y="96" textAnchor="middle" fontSize="10" fill="var(--mut)">{centerLabel}</text>
      </svg>
      <ul className="space-y-1.5 text-sm">
        {data.map((d, i) => (
          <li key={d.label} className="flex items-center gap-2"><i className="inline-block h-3 w-3 rounded-sm" style={{ background: PALETTE[i % PALETTE.length] }} />{d.label} <b>{d.value}</b>
            <span className="text-xs text-mut">({Math.round((d.value / total) * 100)}%)</span></li>))}
      </ul>
    </div>
  )
}

/** Two-series line chart over time. points: [{ label, a, b }]. */
export function LineChart({ points, aLabel, bLabel }) {
  const ref = useRef(null)
  const W = 520
  const H = 170
  const pad = 26
  const max = Math.max(1, ...points.flatMap((p) => [p.a, p.b]))
  const x = (i) => (points.length === 1 ? W / 2 : pad + (i * (W - pad * 2)) / (points.length - 1))
  const y = (v) => H - pad - (v / max) * (H - pad * 2)
  const path = (k) => points.map((p, i) => `${i ? 'L' : 'M'}${x(i)},${y(p[k])}`).join(' ')
  useEffect(() => {
    if (reduced() || !ref.current) return undefined
    const lines = ref.current.querySelectorAll('path.ln')
    const tws = [...lines].map((l) => { const len = l.getTotalLength?.() || 0; return gsap.fromTo(l, { strokeDasharray: len, strokeDashoffset: len }, { strokeDashoffset: 0, duration: 1.2, ease: 'power2.out' }) })
    return () => tws.forEach((t) => t.kill())
  }, [points])
  return (
    <div ref={ref}>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={`Line chart of ${aLabel} and ${bLabel} by day`}>
        {[0, 0.5, 1].map((g) => <line key={g} x1={pad} x2={W - pad} y1={y(max * g)} y2={y(max * g)} stroke="var(--line)" strokeDasharray="3 4" />)}
        <path className="ln" d={path('a')} fill="none" stroke="var(--brand)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        <path className="ln" d={path('b')} fill="none" stroke="var(--mint)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="1" />
        {points.map((p, i) => (<g key={p.label}><circle cx={x(i)} cy={y(p.a)} r="4" fill="var(--brand)" /><circle cx={x(i)} cy={y(p.b)} r="4" fill="var(--mint)" />
          <text x={x(i)} y={H - 6} textAnchor="middle" fontSize="10" fill="var(--mut)">{p.label.slice(5)}</text></g>))}
      </svg>
      <p className="mt-1 flex gap-4 text-xs text-mut"><span><i className="mr-1 inline-block h-2 w-4 rounded" style={{ background: 'var(--brand)' }} />{aLabel}</span><span><i className="mr-1 inline-block h-2 w-4 rounded" style={{ background: 'var(--mint)' }} />{bLabel}</span></p>
    </div>
  )
}

/** Horizontal bars with labels and values. items: [{ label, value, hint }]. */
export function BarList({ items }) {
  const ref = useRef(null)
  const max = Math.max(1, ...items.map((i) => i.value))
  useEffect(() => {
    if (!ref.current) return undefined
    const els = ref.current.querySelectorAll('.bar > i')
    if (reduced()) { els.forEach((e) => { e.style.width = `${e.dataset.w}%` }); return undefined }
    const tw = gsap.to(els, { width: (i, el) => `${el.dataset.w}%`, duration: 0.9, ease: 'power3.out', stagger: 0.06 })
    return () => tw.kill()
  }, [items])
  return (
    <ul ref={ref} className="space-y-3">
      {items.map((it) => (
        <li key={it.label} className="grid grid-cols-[8.5rem_1fr_2rem] items-center gap-3 text-sm">
          <span title={it.hint}>{it.label}</span><div className="bar"><i data-w={Math.round((it.value / max) * 100)} /></div><b>{it.value}</b></li>))}
    </ul>
  )
}

/** Circular progress. value of total, with a text label so the number is never only a colour. */
export function Ring({ value, total, label, size = 120 }) {
  const ref = useRef(null)
  const R = 46
  const C = 2 * Math.PI * R
  const pct = total ? value / total : 0
  useEffect(() => {
    if (!ref.current) return undefined
    const arc = ref.current.querySelector('circle.arc')
    if (reduced()) { arc.setAttribute('stroke-dashoffset', String(C * (1 - pct))); return undefined }
    const tw = gsap.fromTo(arc, { strokeDashoffset: C }, { strokeDashoffset: C * (1 - pct), duration: 1, ease: 'power3.out' })
    return () => tw.kill()
  }, [value, total])
  return (
    <div ref={ref} className="flex items-center gap-4">
      <svg width={size} height={size} viewBox="0 0 110 110" role="img" aria-label={`${value} of ${total} ${label}`}>
        <circle cx="55" cy="55" r={R} fill="none" stroke="var(--soft)" strokeWidth="12" />
        <circle className="arc" cx="55" cy="55" r={R} fill="none" stroke="var(--mint)" strokeWidth="12" strokeLinecap="round" strokeDasharray={C} strokeDashoffset={C} transform="rotate(-90 55 55)" />
        <text x="55" y="53" textAnchor="middle" fontSize="22" fontWeight="800" fill="var(--ink)">{value}/{total}</text>
        <text x="55" y="70" textAnchor="middle" fontSize="9" fill="var(--mut)">{label}</text>
      </svg>
    </div>
  )
}

/** One bar split into labelled parts (for example: not triaged / flagged / dismissed). */
export function StackBar({ parts }) {
  const ref = useRef(null)
  const total = parts.reduce((a, p) => a + p.value, 0) || 1
  useEffect(() => {
    if (!ref.current) return undefined
    const els = ref.current.querySelectorAll('[data-w]')
    if (reduced()) { els.forEach((e) => { e.style.width = `${e.dataset.w}%` }); return undefined }
    const tw = gsap.to(els, { width: (i, el) => `${el.dataset.w}%`, duration: 0.8, ease: 'power3.out', stagger: 0.08 })
    return () => tw.kill()
  }, [parts])
  return (
    <div ref={ref}>
      <div className="flex h-3 overflow-hidden rounded-full" style={{ background: 'var(--soft)' }} role="img" aria-label={parts.map((p) => `${p.label} ${p.value}`).join(', ')}>
        {parts.map((p, i) => <i key={p.label} data-w={(p.value / total) * 100} style={{ width: 0, background: PALETTE[i % PALETTE.length], display: 'block' }} />)}
      </div>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-mut">{parts.map((p, i) => <li key={p.label}><i className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: PALETTE[i % PALETTE.length] }} />{p.label} <b className="text-ink">{p.value}</b></li>)}</ul>
    </div>
  )
}
