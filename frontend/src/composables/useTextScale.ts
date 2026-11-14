import { computed, ref } from 'vue'

/** A+ text-size cycler: 100% → 125% → 150% → 100%. Applied as a class on <html>. */
const STEPS = [100, 125, 150] as const
type Step = (typeof STEPS)[number]
const STORAGE_KEY = 'groweire:text-scale'

function readStored(): Step {
  try {
    const value = Number(localStorage.getItem(STORAGE_KEY))
    return (STEPS as readonly number[]).includes(value) ? (value as Step) : 100
  } catch {
    return 100
  }
}

const scale = ref<Step>(100)

function apply(step: Step) {
  const root = document.documentElement
  root.classList.remove('text-125', 'text-150')
  if (step !== 100) root.classList.add(`text-${step}`)
}

/** Call once at app start so the stored preference applies before first paint of content. */
export function initTextScale() {
  scale.value = readStored()
  apply(scale.value)
}

export function useTextScale() {
  function cycle() {
    const next = STEPS[(STEPS.indexOf(scale.value) + 1) % STEPS.length]!
    scale.value = next
    apply(next)
    try {
      localStorage.setItem(STORAGE_KEY, String(next))
    } catch {
      /* storage unavailable: the setting just won't persist */
    }
  }

  const percent = computed(() => `${scale.value}%`)
  const label = computed(() => `Text size: ${scale.value}%. Make text bigger`)

  return { scale, percent, cycle, label }
}
