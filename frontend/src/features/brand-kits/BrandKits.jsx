import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../lib/apiClient.js'
import { useAuth } from '../../lib/auth.jsx'
import { useLoad } from '../../lib/useLoad.js'
import { KIT_STATE_LABEL } from '../../lib/formatters.js'
import { useStagger } from '../../lib/motion.js'
import { Button, EmptyState, ErrorBanner, PageHeader, Spinner, Stepper, StatusTag } from '../../components/ui/index.jsx'
import KitActions from './KitActions.jsx'

const KIT_STEPS = ['Guidelines added', 'Rules confirmed', 'Sent to creators', 'In use']
const stageOf = (k) => ({ needs_confirmation: 1, ready_to_send: 2, live: k.reviews_count > 0 ? 3 : 2, inactive: 3 }[k.state])
const NEXT = { needs_confirmation: 'Next for you: confirm the proposed rules.', ready_to_send: 'Next for you: send this kit to creators.', live: 'Live. Creators can start checking posts.', inactive: 'Inactive. Creators cannot start new posts with it.' }

export default function BrandKits() {
  const { user } = useAuth()
  const kits = useLoad(() => api('/brand-kits'))
  const nav = useNavigate()
  const list = useRef(null)
  const [busy, setBusy] = useState(false)
  const [drag, setDrag] = useState(false)
  const [error, setError] = useState(null)
  const [url, setUrl] = useState('')
  useStagger(list, '.rv', [kits.data])

  async function start(call) {
    setBusy(true); setError(null)
    try { const r = await call(); nav(`/brand-kits/${r.kit_id}`) } catch (err) { setError(err) } finally { setBusy(false) }
  }
  const upload = (file) => { if (!file) return; const form = new FormData(); form.append('file', file); start(() => api('/brand-kits/extract', { method: 'POST', form })) }
  const importDoc = (e) => { e.preventDefault(); start(() => api('/brand-kits/extract-google-doc', { method: 'POST', body: { url } })) }
  const isAdmin = user.role === 'admin'
  return (
    <>
      <PageHeader title="Brand Kits" subtitle={isAdmin ? 'Add guidelines, confirm the rules, then send the kit to creators.' : 'The brand rules the admin sent you. Reviewers check posts against these.'} />
      <ErrorBanner error={error} />
      {isAdmin && (
        <div className="mb-6 grid gap-4 lg:grid-cols-[2fr_1fr]">
          <label htmlFor="kit-file" onDragOver={(e) => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files?.[0]) }}
            className="block cursor-pointer rounded-3xl border-2 border-dashed p-8 text-center transition-colors"
            style={{ borderColor: drag ? 'var(--brand)' : 'var(--line)', background: drag ? 'var(--soft)' : 'var(--card)' }}>
            <input id="kit-file" type="file" accept=".pdf,.docx" className="sr-only" disabled={busy} onChange={(e) => { upload(e.target.files?.[0]); e.target.value = '' }} />
            <p className="text-lg font-bold">{busy ? 'Reading your guidelines and proposing rules…' : 'Drop a guideline PDF or DOCX here, or click to choose'}</p>
            <p className="mt-1 text-sm text-mut">Text PDFs, DOCX, and scanned PDFs (read with OCR when installed). Up to 10 MB. Rules stay candidates until you confirm them.</p>
          </label>
          <form onSubmit={importDoc} className="card space-y-2">
            <label className="label" htmlFor="gdoc">Or import a Google Doc</label>
            <input id="gdoc" className="input" placeholder="https://docs.google.com/document/d/…" value={url} onChange={(e) => setUrl(e.target.value)} />
            <p className="text-xs text-mut">The doc must be shared as “Anyone with the link can view”.</p>
            <Button type="submit" variant="alt" busy={busy} disabled={!url.trim()}>Import</Button>
          </form>
        </div>
      )}
      {kits.loading && !kits.data ? <Spinner /> : kits.error ? <ErrorBanner error={kits.error} onRetry={kits.reload} /> :
        !kits.data.kits.length ? (
          <EmptyState title={isAdmin ? 'No Brand Kits yet' : 'No Brand Kit has been sent to you yet'}>{isAdmin ? 'Upload your brand guidelines above to create the first kit.' : 'You will see kits here once the admin sends one. Your to-do list on Home will tell you.'}</EmptyState>
        ) : (
          <ul ref={list} className="grid gap-4">
            {kits.data.kits.map((k) => (
              <li key={k.id} className="card rv space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <Link className="text-lg font-bold text-brand hover:underline" to={`/brand-kits/${k.id}`}>{k.name}</Link>
                    <p className="text-xs text-mut">{k.active_version_number ? `Version ${k.active_version_number}` : 'Not confirmed yet'} · {k.reviews_count} post(s) checked</p>
                  </div>
                  <StatusTag status={k.state} label={KIT_STATE_LABEL[k.state]} />
                </div>
                {isAdmin && (<>
                  <Stepper steps={KIT_STEPS} current={stageOf(k)} />
                  <p className="text-sm text-mut">{NEXT[k.state]}</p>
                  <KitActions kit={k} onDone={kits.reload} />
                </>)}
                {user.role === 'creator' && <Link to="/posts/new" className="btn inline-block !py-2">Create a post with this kit</Link>}
              </li>
            ))}
          </ul>)}
    </>
  )
}
