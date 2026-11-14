import type { Schemas } from './api'
import { MAX_PRIORITIES, type Answers, type Priority } from './query'

/**
 * Tap a "what matters" card. The order of taps is the rank; tapping a picked card removes it.
 * A fourth pick is refused (`full`), so the caller can say why nothing happened.
 */
export function togglePriority(picked: Priority[], id: Priority): { picked: Priority[]; full: boolean } {
  if (picked.includes(id)) return { picked: picked.filter((item) => item !== id), full: false }
  if (picked.length >= MAX_PRIORITIES) return { picked, full: true }
  return { picked: [...picked, id], full: false }
}

/** The crop the risk is weighed for: what grew here last year. */
export function riskCrop(answers: Answers): string | null {
  return answers.crops[0] ?? null
}

/**
 * The rotation we send to the API, oldest year first. Last year is required. A year the farmer
 * was not sure about counts as the crop they grow most often, so we never invent a new crop.
 */
export function rotationFromCrops(crops: (string | null)[]): string[] | null {
  if (!crops[0]) return null
  const counts = new Map<string, number>()
  for (const id of crops) if (id) counts.set(id, (counts.get(id) ?? 0) + 1)
  // Most frequent; last year's crop wins a tie
  const usual = [...counts.entries()].sort((a, b) => b[1] - a[1] || (a[0] === crops[0] ? -1 : 1))[0]![0]
  return crops.map((id) => id ?? usual).reverse()
}

/** Body for `POST /rotations/compare`, or null until last year's crop is known. */
export function buildCompareBody(fieldId: string, answers: Answers): Schemas['CompareIn'] | null {
  const rotation = rotationFromCrops(answers.crops)
  if (!rotation) return null
  return {
    field_id: fieldId,
    current_rotation: rotation,
    priorities: answers.priorities,
    constraints: {
      has_livestock: answers.livestock,
      irrigation: false,
      // Not asked: the API treats null as "unknown" and lists it as a gap, not as a filter
      equipment: null,
      excluded_crops: answers.excluded,
      must_include: [],
      market_contracts: answers.contracts,
    },
    n_alternatives: 3,
  }
}
