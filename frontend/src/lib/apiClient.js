const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const KEY = 'brandsure.token'
const RKEY = 'brandsure.refresh'

export class ApiError extends Error {
  constructor(status, code, message, requestId) { super(message); this.status = status; this.code = code; this.requestId = requestId }
}

export const getToken = () => { try { return localStorage.getItem(KEY) } catch { return null } }
export const setToken = (t) => { try { if (t) localStorage.setItem(KEY, t); else localStorage.removeItem(KEY) } catch { /* storage unavailable */ } }

export const getRefresh = () => { try { return localStorage.getItem(RKEY) } catch { return null } }
export const setRefresh = (t) => { try { if (t) localStorage.setItem(RKEY, t); else localStorage.removeItem(RKEY) } catch { /* storage unavailable */ } }

let refreshing = null
async function tryRefresh() {
  const rt = getRefresh()
  if (!rt) return false
  refreshing = refreshing || fetch(`${BASE}/auth/refresh`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: rt }) })
    .then(async (r) => { if (!r.ok) return false; const d = await r.json(); setToken(d.token); setRefresh(d.refresh_token); return true })
    .catch(() => false).finally(() => { refreshing = null })
  return refreshing
}

export async function api(path, opts = {}, retried = false) {
  const { method = 'GET', body, form } = opts
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let payload
  if (form) payload = form
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body) }
  let res
  try { res = await fetch(BASE + path, { method, headers, body: payload }) }
  catch { throw new ApiError(0, 'NETWORK', 'Cannot reach the API. Check that the backend is running on port 8000.') }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const e = data.error || {}
    if (res.status === 401 && !path.startsWith('/auth/') && !retried && await tryRefresh()) return api(path, opts, true)
    if (res.status === 401 && !path.startsWith('/auth/')) { setToken(null); setRefresh(null); window.dispatchEvent(new Event('brandsure:logout')) }
    throw new ApiError(res.status, e.code || 'ERROR', e.message || 'Request failed.', e.request_id)
  }
  return data
}
