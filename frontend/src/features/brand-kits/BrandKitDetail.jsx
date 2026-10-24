import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../../lib/apiClient.js'
import { useAuth } from '../../lib/auth.jsx'
import { useLoad } from '../../lib/useLoad.js'
import { KIT_STATE_LABEL, RULE_LABEL } from '../../lib/formatters.js'
import { useStagger } from '../../lib/motion.js'
import { Button, EmptyState, ErrorBanner, PageHeader, Spinner, StatusTag, Tag } from '../../components/ui/index.jsx'
import KitActions from './KitActions.jsx'
import CandidateRuleCard from './CandidateRuleCard.jsx'

const BLANK = {
  preferred_term: { params: { preferred: '', variants: [] } }, banned_term: { params: { banned: '' } },
  expiry: { valid_until: null, params: { keywords: [] } }, required_disclaimer: { params: { phrase: '' } },
  claim_rule: { params: { patterns: [] } }, tone_guideline: { params: { avoid_words: [] } }, fact: { params: {} },
  palette: { params: { colors: [] } }, accessibility: { params: { require_alt: true, min_contrast: 4.5 } },
}

export default function BrandKitDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const { user } = useAuth()
  const { data, error, loading, reload } = useLoad(() => api(`/brand-kits/${id}`), [id])
  const [rules, setRules] = useState([])
  const [editing, setEditing] = useState(false)
  const [newType, setNewType] = useState('preferred_term')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const list = useRef(null)
  useEffect(() => { if (data?.extraction) { setRules(data.extraction.candidates); setEditing(true) } }, [data])
  useStagger(list, '.rv', [data, editing])

  if (loading && !data) return <Spinner />
  if (error) return <ErrorBanner error={error} onRetry={reload} />
  const { kit, version, extraction } = data
  const isAdmin = user.role === 'admin'
  const pending = !!extraction
  const missingDate = rules.some((c) => c.type === 'expiry' && !c.valid_until)

  const startNewVersion = () => {
    setRules(data.rules.map((r) => ({ ...r, id: r.id, confidence: 'high', source: r.source })))
    setEditing(true)
  }
  const addRule = () => setRules([...rules, { id: `new_${Date.now()}`, type: newType, title: RULE_LABEL[newType], content: '', severity: 'medium', valid_until: null, source: null, ...BLANK[newType] }])
  async function confirm() {
    setBusy(true); setErr(null)
    const payload = rules.map((c) => ({ type: c.type, title: c.title, content: c.content, severity: c.severity,
      valid_until: c.valid_until || null, params: c.params || {}, source: c.source || null }))
    try { await api(`/brand-kits/${id}/confirm`, { method: 'POST', body: { rules: payload } }); setEditing(false); reload() }
    catch (e) { setErr(e) } finally { setBusy(false) }
  }

  if (editing && isAdmin) {
    return (
      <>
        <PageHeader title={pending ? `Confirm ${kit.name}` : `New version of ${kit.name}`}
          subtitle={pending ? 'These rules were proposed from your document. Nothing is approved until you confirm.' : 'Edit the rules, then confirm to publish a new version. Existing reviews stay pinned to the version they used.'}>
          {!pending && <Button variant="alt" onClick={() => setEditing(false)}>Cancel</Button>}
          <Button busy={busy} disabled={!rules.length || missingDate} onClick={confirm}>Confirm Brand Kit ({rules.length} rules)</Button>
        </PageHeader>
        <ErrorBanner error={err} />
        {extraction?.warnings.map((w) => <p key={w} role="note" className="mb-2 rounded-2xl border p-3 text-sm t-medium" style={{ borderColor: 'var(--warn)' }}>{w}</p>)}
        <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
          <div>
            <div className="card mb-4 flex flex-wrap items-center gap-2 !py-3">
              <label htmlFor="nt" className="text-sm font-semibold">Add a rule</label>
              <select id="nt" className="input !w-auto" value={newType} onChange={(e) => setNewType(e.target.value)}>
                {Object.entries(RULE_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
              <Button variant="alt" onClick={addRule}>Add</Button>
            </div>
            {rules.length ? (
              <ul ref={list} className="space-y-4">
                {rules.map((c, i) => <CandidateRuleCard key={c.id} rule={c} candidate={pending}
                  onChange={(n) => setRules(rules.map((x, j) => (j === i ? n : x)))} onRemove={() => setRules(rules.filter((_, j) => j !== i))} />)}
              </ul>
            ) : <EmptyState title="No rules yet">Add a rule above, or reload to restore the extracted candidates.</EmptyState>}
          </div>
          {extraction && (
            <aside className="card h-fit lg:sticky lg:top-24"><h2 className="mb-2 font-bold">Extracted text</h2>
              <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap text-xs">{extraction.text}</pre></aside>)}
        </div>
      </>
    )
  }
  return (
    <>
      <PageHeader title={kit.name} subtitle={version ? `Version ${version.version_number} · confirmed ${new Date(version.confirmed_at).toLocaleDateString()}${data.document ? ` · source: ${data.document.filename}` : ''}` : 'Not confirmed yet'}>
        {isAdmin && version && <Button variant="alt" onClick={startNewVersion}>Create new version</Button>}
        {user.role === 'creator' && version && <Link to="/posts/new" className="btn inline-block">Create post</Link>}
      </PageHeader>
      <div className="mb-4 flex flex-wrap items-center gap-3"><StatusTag status={kit.state} label={KIT_STATE_LABEL[kit.state]} />
        {isAdmin && <KitActions kit={kit} onDone={reload} onDeleted={() => nav('/brand-kits')} />}</div>
      {!version && <EmptyState title="Waiting for confirmation">{isAdmin ? 'Reload to continue confirming the extracted rules.' : 'A Brand Admin still has to confirm this kit.'}</EmptyState>}
      <ul ref={list} className="grid gap-3">
        {data.rules.map((r) => (
          <li key={r.id} className="card rv">
            <div className="mb-1 flex flex-wrap gap-1"><Tag tone="ok">Approved</Tag><Tag tone="brand">{RULE_LABEL[r.type]}</Tag><Tag tone="low">{r.severity}</Tag></div>
            <p className="font-bold">{r.title}</p>
            <p className="text-sm text-mut">{r.content}</p>
            {r.valid_until && <p className="mt-1 text-xs text-mut">Valid through {r.valid_until}</p>}
            {r.type === 'palette' && <div className="mt-2 flex gap-2">{(r.params.colors || []).map((c) => <span key={c} title={c} className="h-6 w-6 rounded-md border border-line" style={{ background: c }} />)}</div>}
          </li>
        ))}
      </ul>
    </>
  )
}
