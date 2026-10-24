import { useState } from 'react'
import { Button, SeverityTag, Tag } from '../../components/ui/index.jsx'
import { EVIDENCE_LABEL, FLAG_STATUS, TYPE_LABEL, VERDICT_LABEL } from '../../lib/formatters.js'

const VERDICT_TONE = { supported: 'ok', contradicted: 'high', unverified: 'medium' }
const ORIGIN = { rule: 'Brand Kit rule', ai: 'AI-assisted', reviewer: 'Reviewer' }

/**
 * One finding. mode="reviewer": triage it (flag for the creator / dismiss).
 * mode="creator": a flag raised by the reviewer: accept the suggestion, edit the text or mark it fixed.
 * mode="view": read only.
 */
export default function FlagCard({ f, mode, active, onSelect, onTriage, onCreator, image }) {
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState(f.final_text ?? f.replacement ?? (f.span ? f.quoted_text : ''))
  const hasFix = f.replacement != null
  const creatorDone = ['accepted', 'edited', 'resolved'].includes(f.status)
  return (
    <li id={`finding-${f.id}`} className="card rv" style={{ outline: active ? '3px solid var(--brand)' : 'none', opacity: f.status === 'dismissed' ? 0.55 : 1, borderLeft: `4px solid ${f.status === 'flagged' ? 'var(--bad)' : f.status === 'dismissed' ? 'var(--line)' : creatorDone ? 'var(--ok)' : 'var(--warn)'}` }}>
      <button className="w-full text-left" onClick={onSelect} aria-expanded={active}>
        <div className="mb-1 flex flex-wrap items-center gap-y-1">
          <b className="mr-2">{TYPE_LABEL[f.type]}</b>
          <SeverityTag severity={f.severity} />
          <Tag tone={f.origin === 'reviewer' ? 'medium' : 'low'}>{ORIGIN[f.origin]}{f.origin === 'reviewer' && f.meta?.author ? `: ${f.meta.author}` : ''}</Tag>
          {f.verdict && <Tag tone={VERDICT_TONE[f.verdict]}>{VERDICT_LABEL[f.verdict]}</Tag>}
          <Tag tone={f.status === 'flagged' ? 'high' : creatorDone ? 'ok' : 'low'}>{mode === 'creator' && f.status === 'flagged' ? FLAG_STATUS.flagged : FLAG_STATUS[f.status]}</Tag>
        </div>
        <div className="flex items-center gap-3 text-sm">
          {image && <img src={image.thumb} alt="" className="h-10 w-10 rounded-lg object-cover" />}
          <span><span className="text-mut">{f.span ? 'Text: ' : 'Where: '}</span>{f.span ? `“${f.quoted_text}”` : f.quoted_text}</span>
        </div>
      </button>
      {active && (
        <div className="mt-3 space-y-3 border-t border-line pt-3 text-sm">
          <p>{f.explanation}</p>
          <div>
            <p className="font-semibold">Why it was flagged: <span className="font-normal">{EVIDENCE_LABEL[f.evidence_status] || f.evidence_status}</span></p>
            {f.source_refs.map((s) => <blockquote key={s.id} className="quote"><span className="text-mut">{s.title}: </span>{s.quote}</blockquote>)}
            {!f.source_refs.length && f.origin !== 'reviewer' && <p className="text-mut">No approved source is cited for this finding.</p>}
          </div>
          {f.uncertainty && <p className="t-medium">Uncertainty: {f.uncertainty}</p>}
          {f.suggested_fix && <p><b>Suggested fix: </b>{f.suggested_fix}</p>}

          {mode === 'reviewer' && (
            <div className="flex flex-wrap gap-2">
              {f.status === 'open' && (<><Button onClick={() => onTriage(f.id, 'flag')}>Flag for creator</Button><Button variant="alt" onClick={() => onTriage(f.id, 'dismiss')}>Dismiss: not an issue</Button></>)}
              {f.status === 'flagged' && <Button variant="alt" onClick={() => onTriage(f.id, 'reopen')}>Unflag</Button>}
              {f.status === 'dismissed' && <Button variant="alt" onClick={() => onTriage(f.id, 'reopen')}>Undo dismiss</Button>}
            </div>)}

          {mode === 'creator' && (editing ? (
            <div className="space-y-2">
              <label className="label" htmlFor={`edit-${f.id}`}>Replace “{f.quoted_text}” with</label>
              <textarea id={`edit-${f.id}`} rows={2} className="input" value={text} onChange={(e) => setText(e.target.value)} />
              <div className="flex gap-2"><Button onClick={() => { onCreator(f.id, 'edited', text); setEditing(false) }}>Save edit</Button><Button variant="alt" onClick={() => setEditing(false)}>Cancel</Button></div>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {f.status === 'flagged' && hasFix && <Button onClick={() => onCreator(f.id, 'accepted', null)}>Accept suggestion</Button>}
              {f.status === 'flagged' && f.span && <Button variant="alt" onClick={() => setEditing(true)}>Edit text</Button>}
              {f.status === 'flagged' && <Button variant="alt" onClick={() => onCreator(f.id, 'resolved', null)}>{f.span ? 'Mark as fixed' : 'I fixed this'}</Button>}
              {f.status !== 'flagged' && <Button variant="alt" onClick={() => onCreator(f.id, 'flagged', null)}>Undo</Button>}
            </div>
          ))}
        </div>
      )}
    </li>
  )
}
