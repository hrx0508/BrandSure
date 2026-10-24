import { useState } from 'react'
import { api } from '../../lib/apiClient.js'
import { contrastRatio } from '../../lib/color.js'
import { Button, ErrorBanner } from '../../components/ui/index.jsx'

function ImageRow({ im, editable, reviewId, onChanged, onError, aiEnabled }) {
  const [alt, setAlt] = useState(im.alt_text || '')
  const [fg, setFg] = useState(im.text_color || '#111111')
  const [bg, setBg] = useState(im.bg_color || '#FFFFFF')
  const has = !!(im.text_color && im.bg_color)
  const patch = async (body) => {
    try { await api(`/reviews/${reviewId}/images/${im.id}`, { method: 'PATCH', body }); onChanged('Image details saved.') }
    catch (e) { onError(e) }
  }
  const [ai, setAi] = useState(false)
  const suggest = async () => {
    setAi(true)
    try { const r = await api(`/reviews/${reviewId}/images/${im.id}/suggest-alt`, { method: 'POST' }); setAlt(r.suggestion); await patch({ alt_text: r.suggestion }) }
    catch (e) { onError(e) } finally { setAi(false) }
  }
  const ratio = contrastRatio(fg, bg)
  return (
    <li className="flex gap-3 rounded-2xl border border-line p-3">
      <img src={im.thumb} alt={im.alt_text || `Attached image ${im.filename} (no alt text yet)`} className="h-20 w-20 flex-none rounded-xl object-cover" />
      <div className="min-w-0 flex-1 space-y-2">
        <p className="truncate text-sm font-semibold">{im.filename} <span className="font-normal text-mut">{im.width}×{im.height}</span></p>
        <div className="flex gap-1" aria-label="Dominant colours">{(im.dominant || []).slice(0, 4).map((d) => <span key={d.hex} title={`${d.hex} ${Math.round(d.share * 100)}%`} className="h-4 w-4 rounded border border-line" style={{ background: d.hex }} />)}</div>
        <div><label className="label !text-xs" htmlFor={`alt-${im.id}`}>Alt text</label>
          <input id={`alt-${im.id}`} className="input" disabled={!editable} value={alt} placeholder="Describe the image for screen readers"
            onChange={(e) => setAlt(e.target.value)} onBlur={() => { if (alt !== (im.alt_text || '')) patch({ alt_text: alt }) }} />
          {editable && aiEnabled && <button className="mt-1 text-xs text-brand underline" disabled={ai} onClick={suggest}>{ai ? 'Thinking…' : 'Suggest alt text with AI'}</button>}</div>
        {has ? (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <label>Text <input type="color" disabled={!editable} value={fg} onChange={(e) => setFg(e.target.value)} onBlur={() => { if (fg.toUpperCase() !== im.text_color) patch({ text_color: fg }) }} /></label>
            <label>on <input type="color" disabled={!editable} value={bg} onChange={(e) => setBg(e.target.value)} onBlur={() => { if (bg.toUpperCase() !== im.bg_color) patch({ bg_color: bg }) }} /></label>
            <span className={ratio >= 4.5 ? 't-ok' : 't-high'}>{ratio.toFixed(1)}:1 {ratio >= 4.5 ? 'passes' : 'is low'}</span>
          </div>
        ) : editable && <button className="text-xs text-brand underline" onClick={() => patch({ text_color: '#111111', bg_color: '#FFFFFF' })}>Add a text/background contrast check</button>}
      </div>
      {editable && <button className="self-start text-xs t-high underline" onClick={async () => {
        try { await api(`/reviews/${reviewId}/images/${im.id}`, { method: 'DELETE' }); onChanged('Image removed.') } catch (e) { onError(e) } }}>Remove</button>}
    </li>
  )
}

export default function ImagePanel({ images, editable, reviewId, onChanged, aiEnabled }) {
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  async function upload(file) {
    if (!file) return
    setBusy(true); setErr(null)
    const form = new FormData()
    form.append('file', file)
    try { await api(`/reviews/${reviewId}/images`, { method: 'POST', form }); onChanged('Image attached. Add alt text so everyone can tell what it shows.') }
    catch (e) { setErr(e) } finally { setBusy(false) }
  }
  if (!editable && !images.length) return <p className="text-sm text-mut">No images on this version.</p>
  return (
    <section className="card" aria-labelledby="img-h">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 id="img-h" className="font-bold">Images</h2>
        {editable && (<label className="btn-alt cursor-pointer">{busy ? 'Uploading…' : 'Attach image'}
          <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" className="sr-only" disabled={busy} onChange={(e) => { upload(e.target.files?.[0]); e.target.value = '' }} /></label>)}
      </div>
      <ErrorBanner error={err} />
      {images.length ? <ul className="space-y-3">{images.map((im) => <ImageRow key={`${im.id}-${im.alt_text}-${im.text_color}-${im.bg_color}`} im={im} editable={editable} reviewId={reviewId} onChanged={onChanged} onError={setErr} aiEnabled={aiEnabled} />)}</ul>
        : <p className="text-sm text-mut">No images attached. The reviewer's checks look at each image's alt text, text contrast and colours. Only a small thumbnail is stored, not the original file.</p>}
    </section>
  )
}
