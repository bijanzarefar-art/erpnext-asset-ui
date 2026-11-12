// POST helper for asset_api write endpoints. Always sends the CSRF header.
// Throws an Error whose .message is Persian and safe to show to the user.

function serverMessage(data) {
  try {
    const msgs = JSON.parse(data._server_messages || '[]')
    const first = msgs.length ? JSON.parse(msgs[0]).message : ''
    return String(first).replace(/<[^>]+>/g, '').replace(/^ASSET_API_[A-Z_]+:\s*/, '')
  } catch {
    return ''
  }
}

export function describeFailure(status, data) {
  const type = data?.exc_type || ''
  if (type === 'CSRFTokenError') return { text: 'نشست منقضی شده است. صفحه را دوباره بارگذاری کنید.', detail: '' }
  if (status === 403 || type === 'PermissionError') return { text: 'شما اجازه انجام این کار را ندارید.', detail: '' }
  if (type === 'DoesNotExistError') return { text: 'مورد درخواستی پیدا نشد.', detail: '' }
  const detail = serverMessage(data || {})
  return { text: 'عملیات انجام نشد.', detail }
}

export async function callApi(method, body = {}) {
  if (!window.csrf_token) {
    const e = new Error('نشست معتبر نیست. صفحه را دوباره بارگذاری کنید.')
    e.detail = ''
    throw e
  }
  let res, data
  try {
    res = await fetch(`/api/method/${method}`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        'X-Frappe-CSRF-Token': window.csrf_token,
      },
      body: JSON.stringify(body),
    })
    data = await res.json().catch(() => ({}))
  } catch {
    const e = new Error('ارتباط با سرور برقرار نشد.')
    e.detail = ''
    throw e
  }
  if (!res.ok) {
    const { text, detail } = describeFailure(res.status, data)
    const e = new Error(text)
    e.detail = detail
    e.status = res.status
    throw e
  }
  return data.message
}
