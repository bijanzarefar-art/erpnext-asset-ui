// Dates are stored Gregorian in ERPNext; Jalali is a display concern only.
const jalali = new Intl.DateTimeFormat('fa-IR-u-ca-persian', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})
const number = new Intl.NumberFormat('fa-IR')

export function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? String(value) : jalali.format(d)
}

export function formatNumber(value) {
  return number.format(Number(value || 0))
}

// ERPNext amounts are in the company currency. Show as-is, label is configurable.
export function formatMoney(value, unit = 'ریال') {
  return `${number.format(Math.round(Number(value || 0)))} ${unit}`
}

export const ASSET_STATUS = {
  Draft: { label: 'پیش‌نویس', theme: 'gray' },
  Submitted: { label: 'ثبت‌شده', theme: 'blue' },
  'Partially Depreciated': { label: 'استهلاک جزئی', theme: 'amber' },
  'Fully Depreciated': { label: 'استهلاک کامل', theme: 'amber' },
  Sold: { label: 'فروخته‌شده', theme: 'gray' },
  Scrapped: { label: 'اسقاط‌شده', theme: 'red' },
  'In Maintenance': { label: 'در تعمیر', theme: 'amber' },
  'Out of Order': { label: 'خارج از سرویس', theme: 'red' },
  Issue: { label: 'تحویل‌شده', theme: 'blue' },
  Receipt: { label: 'دریافت‌شده', theme: 'green' },
  'Capitalized': { label: 'سرمایه‌ای شده', theme: 'green' },
  'Work In Progress': { label: 'در جریان', theme: 'amber' },
}

export function statusMeta(status) {
  return ASSET_STATUS[status] || { label: status || '—', theme: 'gray' }
}

// Turn a frappe-ui resource error into a Persian message. Never show raw server text.
export function friendlyError(err) {
  if (!err) return ''
  const raw = [err.exc_type, err.message, ...(err.messages || [])].join(' ')
  if (/Permission|not permitted|403/i.test(raw)) return 'شما اجازه دسترسی به این بخش را ندارید.'
  if (/not\s*found|DoesNotExist|404/i.test(raw)) return 'مورد درخواستی پیدا نشد.'
  return 'خطایی رخ داد. دوباره تلاش کنید.'
}
