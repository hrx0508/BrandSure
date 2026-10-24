import { useCallback, useEffect, useState } from 'react'

export function useLoad(fn, deps = []) {
  const [state, set] = useState({ data: null, error: null, loading: true })
  const run = useCallback(async () => {
    set((s) => ({ ...s, loading: true, error: null }))
    try { set({ data: await fn(), error: null, loading: false }) }
    catch (e) { set((s) => ({ data: s.data, error: e, loading: false })) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(() => { run() }, [run])
  return { ...state, reload: run }
}
