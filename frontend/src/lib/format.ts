/** Small text helpers. Sentences about risk are never built here: those come from the API. */

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]

export function monthName(month: number): string {
  return MONTH_NAMES[month - 1] ?? ''
}

export function monthShort(month: number): string {
  return monthName(month).slice(0, 3)
}

/** `malting_barley` → `Malting barley`, for ids the API has no display name for. */
export function humanise(id: string): string {
  const words = id.replace(/_/g, ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

/** A share of years as "N in 10", the way the API words its own frequencies. */
export function inTen(frequency: number): string {
  return `${Math.round(frequency * 10)} in 10`
}

/** Whole percent, only for the "More detail" views. */
export function percent(share: number): string {
  return `${Math.round(share * 100)}%`
}

const ACRES_PER_HA = 2.471

export function acres(areaHa: number): number {
  const value = areaHa * ACRES_PER_HA
  return value < 10 ? Math.round(value * 10) / 10 : Math.round(value)
}

/** Area with one decimal only where it matters: 0.5, 2, 10, 12.4. */
export function hectares(areaHa: number): string {
  return String(areaHa < 10 ? Math.round(areaHa * 10) / 10 : Math.round(areaHa))
}

/** "2018", "2018 and 2006", "2018, 2022 and 2006". */
export function listWords(items: (string | number)[]): string {
  if (items.length <= 1) return items.join('')
  return `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`
}
