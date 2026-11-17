import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import {
  answersToQuery,
  parseAnswers,
  parseMonth,
  parseStep,
  STEP_COUNT,
  withStep,
  type Answers,
  type Step,
} from '@/lib/query'
import { router } from '@/router'

export type Section = 'maps' | 'words' | 'sources'

/** What a step says before "Next" may move on: go ahead, stay (it handled it), or a message. */
export type NextGuard = () => Promise<boolean | string> | boolean | string

/**
 * Where the person is in the guided flow and what they have answered. The URL is the source
 * of truth (`/app/field/f_1?s=3&c=…`), so Back in the browser and Back in the app agree, and
 * a link opens on the same answer.
 */
export const useFlowStore = defineStore('flow', () => {
  const route = router.currentRoute

  const fieldId = computed(() => (route.value.params.id as string | undefined) || null)
  /** One of the "More" pages, or null while on the guided steps. */
  const section = computed<Section | null>(() => (route.value.params.section as Section) || null)
  /** Steps 2 to 4 need a field; without one the flow is always on step 1. */
  const step = computed<Step>(() => (fieldId.value ? parseStep(route.value.query.s) : 1))
  const answers = computed<Answers>(() => parseAnswers(route.value.query))
  const month = computed(() => parseMonth(route.value.query.m))

  const isFirst = computed(() => step.value === 1)
  const isLast = computed(() => step.value === STEP_COUNT)

  /** Why "Next" did not move on, in the person's words. Cleared on the next move. */
  const blocked = ref<string | null>(null)
  const busy = ref(false)
  let guard: NextGuard | null = null

  watch(
    () => route.value.fullPath,
    () => {
      blocked.value = null
    },
  )

  function place(target: { step?: Step; field?: string | null; section?: Section | null }) {
    const field = target.field === undefined ? fieldId.value : target.field
    const query = withStep(route.value.query, target.step ?? step.value)
    const sectionParam = target.section ?? ''
    return field
      ? { name: 'field', params: { id: field, section: sectionParam }, query }
      : { name: 'workspace', params: { section: sectionParam }, query }
  }

  function goTo(target: Step, field?: string) {
    return router.push(place({ step: target, field }))
  }

  /** The current step registers its check here; it is dropped when the step leaves the screen. */
  function setGuard(next: NextGuard | null) {
    guard = next
  }

  /** Run the current step's check. True: free to move on. */
  async function passGuard(): Promise<boolean> {
    blocked.value = null
    if (!guard) return true
    busy.value = true
    try {
      const verdict = await guard()
      if (typeof verdict === 'string') blocked.value = verdict
      return verdict === true
    } finally {
      busy.value = false
    }
  }

  async function next() {
    if (isLast.value || busy.value) return
    if (await passGuard()) await goTo((step.value + 1) as Step)
  }

  /** The furthest step reached with each field, so steps already seen stay one tap away. */
  const furthest = ref<Record<string, Step>>({})
  watch(
    [fieldId, step],
    ([id, now]) => {
      if (id && now > (furthest.value[id] ?? 1)) furthest.value = { ...furthest.value, [id]: now }
    },
    { immediate: true },
  )
  const reached = computed<Step>(() =>
    fieldId.value ? (Math.max(furthest.value[fieldId.value] ?? 1, step.value) as Step) : 1,
  )
  /** A step the list can open: any step reached so far, or the one after it (like Next). */
  function canJump(target: Step) {
    return target <= Math.min(reached.value + 1, STEP_COUNT)
  }

  /** Open a step from the step list. Going forward runs the same check as Next. */
  async function jump(target: Step) {
    if (target === step.value || busy.value || !canJump(target)) return
    if (target < step.value) return goTo(target)
    // Step 1's check makes the field and moves to step 2 itself (it then answers false)
    if (await passGuard()) await goTo(target)
  }

  function back() {
    if (!isFirst.value) return goTo((step.value - 1) as Step)
  }

  function openSection(target: Section) {
    return router.push(place({ section: target }))
  }

  /** Leave a "More" page and return to the step the person was on. */
  function backToField() {
    return router.push(place({ section: null }))
  }

  /** Forget this field and its answers, and start again from the map. */
  function startNew() {
    return router.push({ name: 'workspace' })
  }

  /** Change some answers. `replace`, so each tap does not add a Back step. */
  function setAnswers(patch: Partial<Answers>) {
    const { c: _c, p: _p, k: _k, ...rest } = route.value.query
    return router.replace({ query: { ...rest, ...answersToQuery({ ...answers.value, ...patch }) } })
  }

  function setMonth(value: number) {
    return router.replace({ query: { ...route.value.query, m: String(value) } })
  }

  return {
    fieldId,
    section,
    step,
    answers,
    month,
    isFirst,
    isLast,
    blocked,
    busy,
    place,
    goTo,
    setGuard,
    next,
    reached,
    canJump,
    jump,
    back,
    openSection,
    backToField,
    startNew,
    setAnswers,
    setMonth,
  }
})
