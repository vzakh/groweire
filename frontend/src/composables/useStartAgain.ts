import { router } from '@/router'
import { useFieldStore } from '@/stores/field'
import { useMap } from './useMap'

/**
 * "Start again": forget the search, pin, corners, field and answers, switch the satellite view
 * off and show the whole of Ireland, on step 1. The same reset as going back to the landing page.
 */
export function useStartAgain() {
  const field = useFieldStore()
  const { showIreland } = useMap()

  return async function startAgain() {
    field.resetAll()
    showIreland()
    // A bare /app: no field, no step, no answers (and no farm=sample)
    await router.push({ name: 'workspace', params: { section: '' }, query: {} })
  }
}
