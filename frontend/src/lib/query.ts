/**
 * The guided flow keeps its place in the URL (`?s=2`), so the browser's Back button
 * and our own Back button do the same thing, and a shared link opens on the same step.
 */
export const STEP_COUNT = 4
export type Step = 1 | 2 | 3 | 4

type QueryValue = string | null | undefined | (string | null)[]
type Query = Record<string, QueryValue>

/** Read the step from a query value. Anything missing or odd means step 1. */
export function parseStep(value: QueryValue): Step {
  const raw = Array.isArray(value) ? value[0] : value
  const n = Number(raw)
  return Number.isInteger(n) && n >= 1 && n <= STEP_COUNT ? (n as Step) : 1
}

/** A copy of the query on the given step. Step 1 has no `s`, to keep the first link clean. */
export function withStep<Q extends Query>(query: Q, step: Step): Query {
  const { s: _dropped, ...rest } = query
  return step === 1 ? rest : { ...rest, s: String(step) }
}
