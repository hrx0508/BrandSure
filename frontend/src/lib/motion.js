import { useEffect } from 'react'
import gsap from 'gsap'

export { gsap }
export const reduced = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches

/** Fade/slide children matching `selector` inside `ref` whenever `deps` change. Skipped for reduced motion. */
export function useStagger(ref, selector, deps = []) {
  useEffect(() => {
    if (reduced() || !ref.current) return undefined
    const els = ref.current.querySelectorAll(selector)
    if (!els.length) return undefined
    const tw = gsap.fromTo(els, { y: 16, opacity: 0 }, { y: 0, opacity: 1, stagger: 0.06, duration: 0.45, ease: 'power2.out', clearProps: 'transform,opacity' })
    return () => tw.kill()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

/** Grow `.bar > i` elements to their data-w percentage. */
export function useBars(ref, deps = []) {
  useEffect(() => {
    if (!ref.current) return undefined
    const els = ref.current.querySelectorAll('.bar > i[data-w]')
    if (reduced()) { els.forEach((e) => { e.style.width = `${e.dataset.w}%` }); return undefined }
    const tw = gsap.to(els, { width: (i, el) => `${el.dataset.w}%`, duration: 0.9, ease: 'power3.out', stagger: 0.05 })
    return () => tw.kill()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}
