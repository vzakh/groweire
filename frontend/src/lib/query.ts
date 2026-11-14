/**
 * Everything the person has answered lives in the URL, so the browser's Back button and our
 * own Back button agree, and a link sent to an advisor opens on the same answer.
 *
 *   s  step, 1 to 4 (absent = 1)
 *   c  crops grown here, oldest to newest, `-` for "not sure":   c=-,winter_wheat,spring_barley
 *   p  what matters, in the order tapped (first counts most):     p=income_stability,simplicity
 *   k  yes/no answers:  ls1 / ls0  livestock;  ct.<market>  a contract;  x.<crop>  a crop to avoid
 *   m  the month picked on the answer screen, 3 to 10
 */
export const STEP_COUNT = 4
export type Step = 1 | 2 | 3 | 4

/** How many past years we ask about. */
export const YEARS = 4

export const PRIORITIES = [
  'income_stability',
  'simplicity',
  'soil_cover',
  'water_use',
  'forage_value',
  'nitrogen_fixing',
  'pest_break',
  'market_suitability',
] as const
export type Priority = (typeof PRIORITIES)[number]
export const MAX_PRIORITIES = 3

export const FIRST_MONTH = 3
export const LAST_MONTH = 10

export interface Answers {
  /** Crop per year, index 0 = last year. `null` = not answered or "not sure". */
  crops: (string | null)[]
  /** Up to three, most important first. */
  priorities: Priority[]
  /** `null` = not answered. */
  livestock: boolean | null
  /** Markets the farm has a contract for, e.g. `malting_barley`. */
  contracts: string[]
  /** Crops the farmer will not grow. */
  excluded: string[]
}

type QueryValue = string | null | undefined | (string | null)[]
type Query = Record<string, QueryValue>

const ID = /^[a-z0-9_]+$/

function first(value: QueryValue): string {
  const raw = Array.isArray(value) ? value[0] : value
  return raw ?? ''
}

function list(value: QueryValue): string[] {
  return first(value)
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

/** Read the step from a query value. Anything missing or odd means step 1. */
export function parseStep(value: QueryValue): Step {
  const n = Number(first(value))
  return Number.isInteger(n) && n >= 1 && n <= STEP_COUNT ? (n as Step) : 1
}

/** A copy of the query on the given step. Step 1 has no `s`, to keep the first link clean. */
export function withStep<Q extends Query>(query: Q, step: Step): Query {
  const { s: _dropped, ...rest } = query
  return step === 1 ? rest : { ...rest, s: String(step) }
}

/** The month picked on the answer screen, or null when none (or an odd value) is in the URL. */
export function parseMonth(value: QueryValue): number | null {
  const n = Number(first(value))
  return Number.isInteger(n) && n >= FIRST_MONTH && n <= LAST_MONTH ? n : null
}

export function emptyAnswers(): Answers {
  return { crops: Array(YEARS).fill(null), priorities: [], livestock: null, contracts: [], excluded: [] }
}

export function parseAnswers(query: Query): Answers {
  const answers = emptyAnswers()

  // URL order is oldest to newest; ours is newest first
  const crops = list(query.c).slice(-YEARS).reverse()
  crops.forEach((id, index) => {
    answers.crops[index] = ID.test(id) ? id : null
  })

  for (const id of list(query.p)) {
    if ((PRIORITIES as readonly string[]).includes(id) && !answers.priorities.includes(id as Priority)) {
      answers.priorities.push(id as Priority)
    }
  }
  answers.priorities = answers.priorities.slice(0, MAX_PRIORITIES)

  for (const token of list(query.k)) {
    if (token === 'ls1') answers.livestock = true
    else if (token === 'ls0') answers.livestock = false
    else if (token.startsWith('ct.') && ID.test(token.slice(3))) answers.contracts.push(token.slice(3))
    else if (token.startsWith('x.') && ID.test(token.slice(2))) answers.excluded.push(token.slice(2))
  }
  return answers
}

/** The `c`, `p`, `k` keys for these answers. A key is absent when there is nothing to say. */
export function answersToQuery(answers: Answers): { c?: string; p?: string; k?: string } {
  const out: { c?: string; p?: string; k?: string } = {}

  if (answers.crops.some(Boolean)) {
    out.c = [...answers.crops]
      .reverse()
      .map((id) => id ?? '-')
      .join(',')
  }
  if (answers.priorities.length) out.p = answers.priorities.join(',')

  const tokens: string[] = []
  if (answers.livestock !== null) tokens.push(answers.livestock ? 'ls1' : 'ls0')
  tokens.push(...answers.contracts.map((id) => `ct.${id}`), ...answers.excluded.map((id) => `x.${id}`))
  if (tokens.length) out.k = tokens.join(',')

  return out
}
