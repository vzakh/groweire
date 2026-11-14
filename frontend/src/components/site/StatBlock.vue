<script setup lang="ts">
/** One stat: a counting number (or fixed word) over a short explanation. */
import { computed, ref } from 'vue'
import { useCountUp } from '@/composables/useCountUp'

const props = defineProps<{
  to?: number
  from?: number
  prefix?: string
  suffix?: string
  /** smaller word after the number, e.g. "NASA Missions" */
  unit?: string
  /** fixed text instead of a counting number */
  word?: string
  text: string
}>()
const el = ref<HTMLElement | null>(null)
const n = useCountUp(el, props.to ?? 0, props.from ?? 0)
const finalText = computed(() =>
  props.word ?? `${props.prefix ?? ''}${props.to}${props.suffix ?? ''}${props.unit ? ` ${props.unit}` : ''}`,
)
</script>

<template>
  <div
    ref="el"
    class="border-t-[3px] border-emerald pt-5"
  >
    <p
      class="font-display text-[clamp(2.25rem,2.75vw,2.6rem)] leading-none font-bold tracking-[-0.04em] text-forest tabular-nums"
      :aria-label="finalText"
    >
      <span
        aria-hidden="true"
        class="whitespace-nowrap"
      >{{ word ?? `${prefix ?? ''}${n}${suffix ?? ''}` }}</span>
      <span
        v-if="unit"
        aria-hidden="true"
        class="ml-1.5 inline-block text-[0.5em] tracking-[-0.02em]"
      >{{ unit }}</span>
    </p>
    <p class="mt-3 text-[1.0625rem] leading-snug text-muted-ink">
      {{ text }}
    </p>
  </div>
</template>
