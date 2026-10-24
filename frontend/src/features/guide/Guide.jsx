import { useRef } from 'react'
import { useAuth } from '../../lib/auth.jsx'
import { useStagger } from '../../lib/motion.js'
import { PageHeader, Tag } from '../../components/ui/index.jsx'

const ROLES = [
  { key: 'admin', title: 'Admin', blurb: 'Owns the rules.', color: 'var(--brand)',
    can: ['Upload guidelines: PDF, DOCX, scanned PDF (OCR) or a Google Doc', 'Confirm or edit the proposed rules, and create new versions', 'Send a Brand Kit to creators', 'Make a kit inactive, activate it again, or delete an unused one', 'Add creators and reviewers to the team', 'Watch every post (read only) and the insights'],
    cannot: ['Create posts', 'Review, approve or reject posts'],
    waiting: ['Creators to start using a sent kit', 'Posts to move between creators and reviewers'] },
  { key: 'creator', title: 'Creator', blurb: 'Writes the posts.', color: 'var(--mint)',
    can: ['Create a post: write it, upload DOCX/PDF, import a Google Doc, attach images', 'Submit it to a reviewer', 'See only what the reviewer flagged, with charts of the red flags', 'Accept a suggestion, edit the text or mark a flag as fixed', 'Save corrections as a new version and resubmit', 'Mark an approved post as published'],
    cannot: ['Run the Brand Kit checks or review posts', 'See findings the reviewer did not flag', 'Approve a post, or change Brand Kits', 'See other creators’ posts'],
    waiting: ['The reviewer to review the post'] },
  { key: 'reviewer', title: 'Reviewer', blurb: 'Checks and decides.', color: 'var(--warn)',
    can: ['See posts creators have submitted', 'Press Start review: BrandSure checks the post against the Brand Kit (and AI if on)', 'Flag real problems for the creator, dismiss false alarms', 'Select text and suggest a replacement, or edit the post directly', 'Approve it, send it back with flags, or reject it with a reason', 'Comment on any post'],
    cannot: ['Create posts', 'Change Brand Kits or rules', 'Review their own post', 'Approve a post before starting its review'],
    waiting: ['The creator to fix what was flagged'] },
]
const STEPS = [
  ['Admin', 'uploads guidelines, confirms the rules and sends the Brand Kit to creators.'],
  ['Creator', 'writes a post (text, document, Google Doc, images) and submits it to a reviewer.'],
  ['Reviewer', 'presses Start review. BrandSure checks the post against the Brand Kit. The reviewer flags what is really wrong and dismisses false alarms.'],
  ['Reviewer', 'adds suggestions or edits the post if needed, then approves it, sends it back with flags, or rejects it.'],
  ['Creator', 'sees only the flagged items (with charts), fixes them and resubmits. This repeats until the reviewer is happy.'],
  ['Reviewer', 'confirms the final version. It is approved. The creator publishes it outside BrandSure and marks it as published.'],
]

export default function Guide() {
  const { user } = useAuth()
  const root = useRef(null)
  useStagger(root, '.rv', [])
  return (
    <div ref={root}>
      <PageHeader title="How it works" subtitle="Each role has its own job. Nobody does another role’s work." />
      <section className="card rv mb-6">
        <h2 className="mb-3 font-bold">The path of a post</h2>
        <ol className="grid gap-3 md:grid-cols-2">
          {STEPS.map(([who, text], i) => (
            <li key={i} className="flex gap-3 rounded-xl border border-line p-3">
              <b className="grid h-8 w-8 flex-none place-items-center rounded-full" style={{ background: 'var(--brand)', color: 'var(--brand-ink)' }}>{i + 1}</b>
              <span className="text-sm"><b>{who}</b> {text}</span></li>))}
        </ol>
        <p className="mt-3 text-sm text-mut">BrandSure never publishes anything itself. “Approved” means a reviewer accepted that exact version.</p>
      </section>
      <div className="grid gap-4 lg:grid-cols-3">
        {ROLES.map((r) => (
          <section key={r.key} className="card rv" style={{ borderColor: user.role === r.key ? r.color : undefined, boxShadow: user.role === r.key ? '0 12px 34px var(--shadow)' : undefined }}>
            <div className="mb-3 flex items-center justify-between"><h2 className="text-xl font-extrabold" style={{ color: r.color }}>{r.title}</h2>{user.role === r.key && <Tag tone="brand">You</Tag>}</div>
            <p className="mb-3 text-sm text-mut">{r.blurb}</p>
            <h3 className="text-sm font-bold">Can</h3><ul className="mb-3 list-disc space-y-1 pl-5 text-sm">{r.can.map((x) => <li key={x}>{x}</li>)}</ul>
            <h3 className="text-sm font-bold">Cannot</h3><ul className="mb-3 list-disc space-y-1 pl-5 text-sm text-mut">{r.cannot.map((x) => <li key={x}>{x}</li>)}</ul>
            <h3 className="text-sm font-bold">Waits for</h3><ul className="list-disc space-y-1 pl-5 text-sm text-mut">{r.waiting.map((x) => <li key={x}>{x}</li>)}</ul>
          </section>))}
      </div>
    </div>
  )
}
