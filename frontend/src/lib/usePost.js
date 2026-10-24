import { useState } from 'react'
import { api } from './apiClient.js'
import { useLoad } from './useLoad.js'

/** Loads one post (optionally an older version) plus its history. Shared by the creator, reviewer and admin screens. */
export function usePost(id) {
  const [ver, setVer] = useState(null)
  const post = useLoad(() => api(`/reviews/${id}${ver ? `?version_number=${ver}` : ''}`), [id, ver])
  const audit = useLoad(() => api(`/reviews/${id}/audit`), [id, post.data?.review.updated_at])
  return { ...post, ver, setVer, audit }
}

/** Highlight segments for a draft: non-overlapping spans, in order. */
export function segments(text, findings) {
  const spans = findings.filter((f) => f.span).sort((a, b) => a.span.start - b.span.start)
  const out = []
  let pos = 0
  for (const f of spans) {
    if (f.span.start < pos) continue // overlapping highlight: still listed in the findings panel
    if (f.span.start > pos) out.push({ t: text.slice(pos, f.span.start) })
    out.push({ t: text.slice(f.span.start, f.span.end), f })
    pos = f.span.end
  }
  if (pos < text.length) out.push({ t: text.slice(pos) })
  return out
}

/** Applies accepted/edited replacements from the end of the text backwards so offsets stay valid. */
export function applyChanges(text, findings) {
  const ch = findings.filter((f) => ['accepted', 'edited'].includes(f.status) && f.span && (f.final_text ?? f.replacement) != null)
    .sort((a, b) => b.span.start - a.span.start)
  let out = text
  let limit = Infinity
  const used = []
  for (const f of ch) {
    if (f.span.end > limit) continue
    out = out.slice(0, f.span.start) + (f.final_text ?? f.replacement) + out.slice(f.span.end)
    limit = f.span.start
    used.push(f)
  }
  return { text: out, used }
}
