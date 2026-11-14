import { computed } from 'vue'
import { defineStore } from 'pinia'
import { parseStep, STEP_COUNT, withStep, type Step } from '@/lib/query'
import { router } from '@/router'

export type Section = 'maps' | 'words' | 'sources'

/**
 * Where the person is in the guided flow. The URL is the source of truth
 * (`/app?s=2`, `/app/words`), so Back in the browser and Back in the app agree.
 */
export const useFlowStore = defineStore('flow', () => {
  const route = router.currentRoute

  const step = computed<Step>(() => parseStep(route.value.query.s))
  /** One of the "More" pages, or null while on the guided steps. */
  const section = computed<Section | null>(() => (route.value.params.section as Section) || null)

  const isFirst = computed(() => step.value === 1)
  const isLast = computed(() => step.value === STEP_COUNT)

  function goTo(target: Step) {
    return router.push({ name: 'workspace', query: withStep(route.value.query, target) })
  }
  function next() {
    if (!isLast.value) return goTo((step.value + 1) as Step)
  }
  function back() {
    if (!isFirst.value) return goTo((step.value - 1) as Step)
  }
  /** Leave a "More" page and return to the step the person was on. */
  function backToField() {
    return router.push({ name: 'workspace', query: route.value.query })
  }

  return { step, section, isFirst, isLast, goTo, next, back, backToField }
})
