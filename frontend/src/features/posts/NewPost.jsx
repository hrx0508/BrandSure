import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { api } from '../../lib/apiClient.js'
import { useAuth } from '../../lib/auth.jsx'
import { useLoad } from '../../lib/useLoad.js'
import { Button, EmptyState, ErrorBanner, PageHeader, Spinner } from '../../components/ui/index.jsx'

export default function NewPost() {
  const { user } = useAuth()
  const kits = useLoad(() => api('/brand-kits'))
  const nav = useNavigate()
  const [f, setF] = useState({ kit_id: '', title: '', content: '', content_type: 'general' })
  const [source, setSource] = useState('text')
  const [file, setFile] = useState(null)
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  if (user.role !== 'creator') return <Navigate to="/posts" replace />
  if (kits.loading && !kits.data) return <Spinner />
  if (kits.error) return <ErrorBanner error={kits.error} onRetry={kits.reload} />
  const active = kits.data.kits.filter((k) => k.state === 'live')
  if (!active.length) return <EmptyState title="No Brand Kit has been sent to you yet">When the admin sends a Brand Kit, you can create posts for it. Your to-do list on Home will tell you.</EmptyState>
  const kitId = f.kit_id || active[0].id
  const ready = (source === 'gdoc' || f.title.trim()) && (source === 'text' ? f.content.trim() : source === 'file' ? file : url.trim())

  async function submit(e) {
    e.preventDefault(); setBusy(true); setErr(null)
    try {
      let r
      if (source === 'text') r = await api('/reviews', { method: 'POST', body: { ...f, kit_id: kitId } })
      else if (source === 'gdoc') r = await api('/reviews/from-google-doc', { method: 'POST', body: { kit_id: kitId, url, title: f.title, content_type: f.content_type } })
      else {
        const form = new FormData()
        form.append('file', file); form.append('kit_id', kitId); form.append('title', f.title); form.append('content_type', f.content_type)
        r = await api('/reviews/upload', { method: 'POST', form })
      }
      nav(`/posts/${r.id}`)
    } catch (x) { setErr(x) } finally { setBusy(false) } // what you typed stays on failure
  }
  return (
    <>
      <PageHeader title="Create post" subtitle="Write your post. You will submit it to a reviewer next; they check it against the Brand Kit." />
      <form onSubmit={submit} className="card max-w-3xl space-y-4">
        <ErrorBanner error={err} />
        <div className="grid gap-4 md:grid-cols-3">
          <div><label className="label" htmlFor="kit">Brand Kit</label>
            <select id="kit" className="input" value={kitId} onChange={(e) => setF({ ...f, kit_id: e.target.value })}>
              {active.map((k) => <option key={k.id} value={k.id}>{k.name} (v{k.active_version_number})</option>)}</select></div>
          <div><label className="label" htmlFor="title">Title</label>
            <input id="title" required={source !== 'gdoc'} className="input" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></div>
          <div><label className="label" htmlFor="ct">Content type</label>
            <select id="ct" className="input" value={f.content_type} onChange={(e) => setF({ ...f, content_type: e.target.value })}>
              <option value="general">General</option><option value="social">Social post</option><option value="email">Email</option><option value="web">Web copy</option><option value="document">Document</option></select></div>
        </div>
        <div role="tablist" className="inline-flex gap-1 rounded-xl bg-soft p-1">
          {[['text', 'Write or paste'], ['file', 'Upload DOCX / PDF'], ['gdoc', 'Google Doc']].map(([k, l]) => (
            <button type="button" role="tab" key={k} aria-selected={source === k} onClick={() => setSource(k)} className="rounded-lg px-4 py-2 text-sm font-semibold"
              style={{ background: source === k ? 'var(--card)' : 'transparent' }}>{l}</button>))}
        </div>
        {source === 'text' ? (
          <div><label className="label" htmlFor="content">Your post</label>
            <textarea id="content" rows={10} className="input !text-base leading-relaxed" value={f.content} onChange={(e) => setF({ ...f, content: e.target.value })} /></div>
        ) : source === 'gdoc' ? (
          <div><label className="label" htmlFor="gurl">Google Doc link</label>
            <input id="gurl" className="input" placeholder="https://docs.google.com/document/d/…" value={url} onChange={(e) => setUrl(e.target.value)} />
            <p className="mt-1 text-xs text-mut">Share the doc as “Anyone with the link can view”. Only the text is imported.</p></div>
        ) : (
          <div><label className="label" htmlFor="file">Document (PDF or DOCX, up to 10 MB)</label>
            <input id="file" type="file" accept=".pdf,.docx" className="input" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            <p className="mt-1 text-xs text-mut">The text is extracted; the file itself is not kept. You can attach images on the next screen.</p></div>
        )}
        <Button type="submit" busy={busy} disabled={!ready}>Create post</Button>
      </form>
    </>
  )
}
