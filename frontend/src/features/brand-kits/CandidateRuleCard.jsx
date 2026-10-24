import { Tag } from '../../components/ui/index.jsx'
import { RULE_LABEL } from '../../lib/formatters.js'

const csv = (v) => (Array.isArray(v) ? v.join(', ') : '')
const list = (s) => s.split(',').map((x) => x.trim()).filter(Boolean)

export default function CandidateRuleCard({ rule, onChange, onRemove, candidate = true }) {
  const set = (patch) => onChange({ ...rule, ...patch })
  const setParam = (k, v) => set({ params: { ...rule.params, [k]: v } })
  const src = rule.source || {}
  const where = src.page ? `page ${src.page}` : src.paragraph ? `paragraph ${src.paragraph}` : 'source'
  const id = `c-${rule.id}`
  const p = rule.params || {}
  return (
    <li className="card space-y-3 rv">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1">
          {candidate && <Tag tone="brand">Candidate</Tag>}<Tag tone="low">{RULE_LABEL[rule.type]}</Tag>
          {rule.confidence === 'low' && <Tag tone="medium">Needs your input</Tag>}
          {src.quote_verified === false && <Tag tone="medium">Edited since extraction</Tag>}
        </div>
        <button className="text-sm t-high underline" onClick={onRemove}>{candidate ? 'Reject' : 'Remove'}</button>
      </div>
      {src.quote && <blockquote className="quote"><span className="text-mut">Evidence ({where}): </span>{src.quote}</blockquote>}
      <div className="grid gap-3 md:grid-cols-2">
        <div><label className="label" htmlFor={`${id}-t`}>Title</label>
          <input id={`${id}-t`} className="input" value={rule.title} onChange={(e) => set({ title: e.target.value })} /></div>
        <div><label className="label" htmlFor={`${id}-s`}>Severity</label>
          <select id={`${id}-s`} className="input" value={rule.severity} onChange={(e) => set({ severity: e.target.value })}>
            <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></div>
      </div>
      <div><label className="label" htmlFor={`${id}-c`}>Rule text</label>
        <textarea id={`${id}-c`} rows={2} className="input" value={rule.content} onChange={(e) => set({ content: e.target.value })} /></div>
      {rule.type === 'preferred_term' && (
        <div className="grid gap-3 md:grid-cols-2">
          <div><label className="label" htmlFor={`${id}-p`}>Preferred form</label>
            <input id={`${id}-p`} className="input" value={p.preferred || ''} onChange={(e) => setParam('preferred', e.target.value)} /></div>
          <div><label className="label" htmlFor={`${id}-v`}>Wrong variants (comma separated)</label>
            <input id={`${id}-v`} className="input" defaultValue={csv(p.variants)} onBlur={(e) => setParam('variants', list(e.target.value))} /></div>
        </div>)}
      {rule.type === 'banned_term' && (
        <div><label className="label" htmlFor={`${id}-b`}>Banned term</label>
          <input id={`${id}-b`} className="input" value={p.banned || ''} onChange={(e) => setParam('banned', e.target.value)} /></div>)}
      {rule.type === 'required_disclaimer' && (
        <div><label className="label" htmlFor={`${id}-d`}>Exact required wording</label>
          <input id={`${id}-d`} className="input" value={p.phrase || ''} onChange={(e) => setParam('phrase', e.target.value)} /></div>)}
      {rule.type === 'expiry' && (
        <div className="grid gap-3 md:grid-cols-2">
          <div><label className="label" htmlFor={`${id}-u`}>Valid through (inclusive, India time)</label>
            <input id={`${id}-u`} type="date" className="input" value={rule.valid_until || ''} onChange={(e) => set({ valid_until: e.target.value || null })} />
            {!rule.valid_until && <p className="mt-1 text-xs t-medium">Enter the exact date; it could not be read reliably.</p>}</div>
          <div><label className="label" htmlFor={`${id}-k`}>Offer keywords in drafts (comma separated)</label>
            <input id={`${id}-k`} className="input" defaultValue={csv(p.keywords)} onBlur={(e) => setParam('keywords', list(e.target.value))} /></div>
        </div>)}
      {rule.type === 'palette' && (
        <div><label className="label" htmlFor={`${id}-pc`}>Approved colours (#RRGGBB, comma separated)</label>
          <input id={`${id}-pc`} className="input" defaultValue={csv(p.colors)} onBlur={(e) => setParam('colors', list(e.target.value).map((c) => c.toUpperCase()))} />
          <div className="mt-2 flex gap-2">{(p.colors || []).map((c) => <span key={c} title={c} className="h-6 w-6 rounded-md border border-line" style={{ background: c }} />)}</div></div>)}
      {rule.type === 'accessibility' && (
        <div className="grid gap-3 md:grid-cols-2">
          <label className="flex items-center gap-2 text-sm font-semibold"><input type="checkbox" checked={p.require_alt !== false} onChange={(e) => setParam('require_alt', e.target.checked)} /> Every image needs alt text</label>
          <div><label className="label" htmlFor={`${id}-mc`}>Minimum contrast ratio</label>
            <input id={`${id}-mc`} type="number" min="1" max="21" step="0.1" className="input" value={p.min_contrast ?? 4.5} onChange={(e) => setParam('min_contrast', Number(e.target.value))} /></div>
        </div>)}
      {rule.type === 'claim_rule' && (
        <div><label className="label" htmlFor={`${id}-cp`}>Claim phrases that need evidence (comma separated)</label>
          <input id={`${id}-cp`} className="input" defaultValue={csv(p.patterns)} onBlur={(e) => setParam('patterns', list(e.target.value))} /></div>)}
      {rule.type === 'tone_guideline' && (
        <div><label className="label" htmlFor={`${id}-aw`}>Words to avoid (comma separated)</label>
          <input id={`${id}-aw`} className="input" defaultValue={csv(p.avoid_words)} onBlur={(e) => setParam('avoid_words', list(e.target.value))} /></div>)}
    </li>
  )
}
