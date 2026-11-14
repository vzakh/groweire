<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronDownIcon } from '@lucide/vue'
import TermHelp from '@/components/common/TermHelp.vue'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { copy } from '@/copy/en'
import type { Schemas } from '@/lib/api'
import { inTen, monthName, percent } from '@/lib/format'
import { STRESS_TYPES, type StressType } from '@/lib/risk'

/**
 * What happened in one month. On top, the API's own words: how often, and the evidence with
 * example years. Under "More detail": every weather type's count, the last 10 years next to
 * the 25, the share with its range, and how much the month matters for the crop.
 * This is counted history, not a prediction, and the wording keeps to the past.
 */
const props = defineProps<{
  month: Schemas['MonthRiskOut']
  /** The crop the risk was weighed for, if any. */
  cropName: string | null
  needsReview: boolean
}>()

const open = ref(false)

/** The most frequent weather type, when it was ever counted. */
const main = computed(() => props.month.counts.find((count) => count.years_hit > 0) ?? null)

const matters = computed(() => {
  const value = props.month.crop_sensitivity
  if (value === null || !props.cropName) return null
  const words = copy.answer.mattersWords
  return copy.answer.matters(props.cropName, value < 0.34 ? words.little : value < 0.67 ? words.some : words.lot)
})

const range = computed(() => {
  const [low, high] = props.month.interval
  return {
    left: `${low * 100}%`,
    width: `${Math.max(1, (high - low) * 100)}%`,
    at: `${props.month.probability * 100}%`,
    text: copy.answer.range(Math.round(low * 10), Math.round(high * 10), props.month.years_total),
  }
})
</script>

<template>
  <section
    aria-live="polite"
    class="flex flex-col gap-3 rounded-xl border-2 border-foreground p-4"
  >
    <h3 class="font-heading text-xl font-bold">
      {{ monthName(month.month) }}: {{ month.label }}, {{ month.frequency_text }}
    </h3>
    <p
      v-for="driver in month.drivers"
      :key="driver.feature"
      data-test="driver"
      class="text-base"
    >
      {{ driver.text }}
    </p>

    <Collapsible v-model:open="open">
      <CollapsibleTrigger as-child>
        <Button
          variant="outline"
          size="tap"
          class="w-full justify-between"
        >
          {{ copy.moreDetail }}
          <ChevronDownIcon
            data-icon="inline-end"
            :class="{ 'rotate-180': open }"
          />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent class="flex flex-col gap-4 pt-4">
        <div>
          <h4 class="mb-2 text-base font-bold">
            {{ copy.answer.allTypes }}
          </h4>
          <ul class="flex flex-col gap-1">
            <li
              v-for="count in month.counts"
              :key="count.stress_type"
              class="flex items-center gap-2 text-base"
            >
              <component
                :is="STRESS_TYPES[count.stress_type as StressType]?.icon"
                class="size-5 shrink-0"
                aria-hidden="true"
              />
              <span class="w-14 font-bold">{{ STRESS_TYPES[count.stress_type as StressType]?.word ?? count.stress_type }}</span>
              <span>{{ copy.answer.ofYears(count.years_hit, count.years_total) }}</span>
            </li>
          </ul>
        </div>

        <p
          v-if="main && main.recent_frequency !== null"
          class="text-base"
        >
          {{ copy.answer.recent(inTen(main.recent_frequency), inTen(main.frequency), main.years_total) }}
        </p>

        <div class="flex flex-col gap-2">
          <p class="text-base">
            {{ copy.answer.share(percent(month.probability)) }}
          </p>
          <div
            class="relative h-4 rounded-full bg-muted ring-1 ring-foreground/30"
            aria-hidden="true"
          >
            <div
              class="absolute inset-y-0 rounded-full bg-foreground/35"
              :style="{ left: range.left, width: range.width }"
            />
            <div
              class="absolute inset-y-[-3px] w-1 -translate-x-1/2 rounded bg-foreground"
              :style="{ left: range.at }"
            />
          </div>
          <p class="text-base">
            {{ range.text }}
          </p>
          <TermHelp term="uncertainty" />
        </div>

        <p
          v-if="matters"
          class="text-base"
        >
          {{ matters }}
        </p>
        <p
          v-if="needsReview"
          class="border-l-4 border-border pl-3 text-base"
        >
          {{ copy.answer.localReview }}
        </p>
      </CollapsibleContent>
    </Collapsible>
  </section>
</template>
