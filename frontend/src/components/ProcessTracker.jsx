import { useEffect, useRef } from 'react'
import { gsap, reduced } from '../lib/motion.js'
import { ActorChip } from './ui/index.jsx'

const LANES = [
  { label: 'Brand Kit sent', actor: 'Admin' },
  { label: 'Post written', actor: 'Creator' },
  { label: 'Reviewer reviews', actor: 'Reviewer' },
  { label: 'Approved', actor: 'Reviewer' },
  { label: 'Published', actor: 'Creator' },
]
const POSITION = { draft: [1, false], changes_requested: [1, false], in_review: [2, false], approved: [4, false], published: [5, false], rejected: [2, true] }
const NEXT_ACTOR = { draft: 'creator', changes_requested: 'creator', in_review: 'reviewer', approved: 'creator' }

/** Who has the ball: shows the whole path, where this post is, and what THIS person should do or is waiting for. */
export function whoIsNext({ review, role, userId, started = false }) {
  const st = review.status
  const next = NEXT_ACTOR[st]
  const creator = review.creator_name || 'the creator'
  const reviewer = review.reviewer_name || 'a reviewer'
  const mine = (next === 'creator' && role === 'creator' && review.created_by === userId)
    || (next === 'reviewer' && role === 'reviewer' && review.created_by !== userId && (!review.reviewer_id || review.reviewer_id === userId))
  const yours = {
    draft: 'Finish your post, attach any images, then submit it to a reviewer.',
    changes_requested: `${reviewer} flagged items. Fix them and resubmit.`,
    in_review: started ? 'Go through the findings: flag what is wrong, dismiss what is not, then decide.' : 'Press Start review. BrandSure checks the post against the Brand Kit and you decide what to flag.',
    approved: 'It was approved. Publish it, then mark it as published.',
  }[st]
  const waiting = {
    draft: `Waiting for ${creator} to finish and submit the post.`,
    changes_requested: `Waiting for ${creator} to fix the flagged items.`,
    in_review: started ? `${reviewer} is reviewing it.` : `Waiting for ${reviewer} to start the review.`,
    approved: `Approved. Waiting for ${creator} to publish it.`,
    published: 'Published. Nothing left to do.',
    rejected: `Rejected by ${reviewer}. The creator can start a new post.`,
  }[st]
  return { mine, text: mine ? yours : waiting }
}

export default function ProcessTracker({ review, role, userId, started = false }) {
  const root = useRef(null)
  const [active, failed] = POSITION[review.status] || [1, false]
  const { mine, text } = whoIsNext({ review, role, userId, started })
  const pct = Math.min(100, (Math.min(active, LANES.length - 1) / (LANES.length - 1)) * 100)

  useEffect(() => {
    if (reduced() || !root.current) return undefined
    const ctx = gsap.context(() => {
      gsap.fromTo('.pt-fill', { width: 0 }, { width: `${pct}%`, duration: 0.9, ease: 'power3.out' })
      gsap.fromTo('.pt-node', { scale: 0.7, opacity: 0 }, { scale: 1, opacity: 1, stagger: 0.07, duration: 0.4, ease: 'back.out(2)' })
      gsap.to('.pt-pulse', { scale: 1.9, opacity: 0, duration: 1.4, repeat: -1, ease: 'power1.out' })
    }, root)
    return () => ctx.revert()
  }, [review.status, pct])

  return (
    <section ref={root} className="card" aria-label="Where this post is in the process" style={{ borderColor: mine ? 'var(--brand)' : undefined }}>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <h2 className="font-bold">Process</h2>
        {review.round > 0 && <span className="chip">Round {review.round}</span>}
        {review.status === 'changes_requested' && <span className="chip" style={{ color: 'var(--warn)' }}>↺ sent back with flags</span>}
      </div>
      <div className="relative overflow-x-auto pb-1">
        <ol className="relative flex min-w-[34rem] justify-between">
          <div className="absolute left-[10%] right-[10%] top-4 h-1 rounded-full" style={{ background: 'var(--line)' }}>
            <div className="pt-fill h-full rounded-full" style={{ width: `${pct}%`, background: failed ? 'var(--bad)' : 'linear-gradient(90deg, var(--brand), var(--mint))' }} />
          </div>
          {LANES.map((l, i) => {
            const done = i < active
            const isActive = i === active
            const bad = isActive && failed
            return (
              <li key={l.label} className="pt-node relative z-10 flex w-1/5 flex-col items-center text-center" aria-current={isActive ? 'step' : undefined}>
                <span className="relative grid h-9 w-9 place-items-center rounded-full border-2 text-sm font-bold"
                  style={{ background: done ? 'var(--brand)' : bad ? 'var(--bad)' : isActive ? 'var(--card)' : 'var(--soft)', color: done || bad ? 'var(--brand-ink)' : isActive ? 'var(--brand)' : 'var(--mut)', borderColor: bad ? 'var(--bad)' : done || isActive ? 'var(--brand)' : 'var(--line)' }}>
                  {isActive && !bad && <i className="pt-pulse absolute inset-0 rounded-full" style={{ background: 'var(--brand)', opacity: 0.35 }} />}
                  <span className="relative">{bad ? '✕' : done ? '✓' : i + 1}</span>
                </span>
                <span className="mt-2 text-xs font-bold" style={{ color: done || isActive ? 'var(--ink)' : 'var(--mut)' }}>{l.label}</span>
                <ActorChip actor={l.actor} />
              </li>
            )
          })}
        </ol>
      </div>
      <p role="status" className="mt-4 rounded-xl px-4 py-3 text-sm font-semibold"
        style={{ background: mine ? 'var(--brand)' : 'var(--soft)', color: mine ? 'var(--brand-ink)' : 'var(--ink)' }}>
        {mine ? 'Your move: ' : ''}{text}
      </p>
    </section>
  )
}
