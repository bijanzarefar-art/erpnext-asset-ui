import { toJalaali, toGregorian, isValidJalaaliDate } from 'jalaali-js'

const FA = '۰۱۲۳۴۵۶۷۸۹'
const AR = '٠١٢٣٤٥٦٧٨٩'

// Accept Persian/Arabic/Latin digits and - or / separators
export function normalizeDigits(s) {
  return String(s ?? '')
    .replace(/[۰-۹]/g, (d) => FA.indexOf(d))
    .replace(/[٠-٩]/g, (d) => AR.indexOf(d))
}

const pad = (n) => String(n).padStart(2, '0')

// '2026-11-06' -> '1405/08/15' (Latin digits; the input is LTR)
export function isoToJalali(iso) {
  if (!iso) return ''
  const [y, m, d] = String(iso).slice(0, 10).split('-').map(Number)
  if (!y || !m || !d) return ''
  const j = toJalaali(y, m, d)
  return `${j.jy}/${pad(j.jm)}/${pad(j.jd)}`
}

// '1405/08/15' -> '2026-11-06', or null when the text is not a valid Jalali date
export function jalaliToIso(text) {
  const parts = normalizeDigits(text).trim().split(/[/\-.]/).map(Number)
  if (parts.length !== 3 || parts.some((n) => !Number.isInteger(n))) return null
  const [jy, jm, jd] = parts
  if (!isValidJalaaliDate(jy, jm, jd)) return null
  const g = toGregorian(jy, jm, jd)
  return `${g.gy}-${pad(g.gm)}-${pad(g.gd)}`
}
