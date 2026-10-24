import { useEffect, useRef, useState } from 'react'
import { gsap, reduced } from '../../lib/motion.js'

const STEPS = ['Checking terminology…', 'Checking claims against approved facts…', 'Checking tone…', 'Checking images and accessibility…']

/** Shown while the real analysis request runs. Purely visual feedback; results always come from the API. */
export default function ScanPanel({ text }) {
  const bar = useRef(null)
  const scan = useRef(null)
  const [i, setI] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setI((x) => Math.min(x + 1, STEPS.length - 1)), 600)
    if (reduced()) return () => clearInterval(id)
    const tl = gsap.timeline()
    tl.to(bar.current, { width: '92%', duration: 2.4, ease: 'power1.out' }, 0)
    tl.fromTo(scan.current, { y: 0 }, { y: 'calc(100% - 26px)', duration: 0.9, repeat: -1, yoyo: true, ease: 'sine.inOut' }, 0)
    return () => { clearInterval(id); tl.kill() }
  }, [])
  return (
    <div role="status" aria-live="polite">
      <div className="bar"><i ref={bar} style={reduced() ? { width: '60%' } : undefined} /></div>
      <p className="py-3 text-center text-sm text-mut">{STEPS[i]}</p>
      <div className="relative overflow-hidden rounded-2xl border border-dashed border-line p-3 text-sm text-mut">
        <div className="max-h-40 overflow-hidden whitespace-pre-wrap">{text}</div>
        {!reduced() && <div ref={scan} className="absolute inset-x-0 top-0 h-[26px]" style={{ background: 'linear-gradient(transparent, color-mix(in srgb, var(--mint) 55%, transparent), transparent)' }} />}
      </div>
    </div>
  )
}
