import { reactive } from 'vue'

// Session-cookie auth against Frappe. The browser never holds API keys.
export const session = reactive({ user: null, ready: false, can: {}, features: {} })

async function post(method, body) {
  if (method !== 'login' && !window.csrf_token) throw Object.assign(new Error('no_csrf_token'), { status: 400 })
  const res = await fetch(`/api/method/${method}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      // Frappe enforces CSRF once the session has a token (see asset_api.api.session.me)
      ...(window.csrf_token ? { 'X-Frappe-CSRF-Token': window.csrf_token } : {}),
    },
    credentials: 'same-origin',
    body: JSON.stringify(body || {}),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    // Never surface Python exception text; callers map by status
    const err = new Error(res.status === 401 ? 'unauthorized' : 'request_failed')
    err.status = res.status
    throw err
  }
  return data.message
}

// Ask the asset_api backend for { user, csrf_token }. No fallback to a stock method:
// that would give a session without a CSRF token and silently weaken write protection.
async function fetchIdentity() {
  const res = await fetch('/api/method/asset_api.api.session.me', { credentials: 'same-origin' })
  if (!res.ok) return { user: null }
  return (await res.json()).message || { user: null }
}

export async function loadSession() {
  try {
    const { user, csrf_token, can, features } = await fetchIdentity()
    session.user = user && user !== 'Guest' ? user : null
    session.can = session.user ? can || {} : {}
    session.features = session.user ? features || {} : {}
    // frappe-ui's frappeRequest sends X-Frappe-CSRF-Token from window.csrf_token
    if (session.user && csrf_token) window.csrf_token = csrf_token
  } catch {
    session.user = null
    session.can = {}
    session.features = {}
  }
  session.ready = true
  return session.user
}

export async function login(usr, pwd) {
  await post('login', { usr, pwd })
  return loadSession()
}

export async function logout() {
  await post('logout')
  session.user = null
  session.can = {}
  session.features = {}
  window.csrf_token = undefined
}
