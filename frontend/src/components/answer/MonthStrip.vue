<script setup lang="ts">
import { CircleCheckIcon } from '@lucide/vue'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { copy } from '@/copy/en'
import type { Schemas } from '@/lib/api'
import { monthShort } from '@/lib/format'
import { STRESS_TYPES, type StressType } from '@/lib/risk'

/**
 * The growing season as eight tiles, March to October. Each tile says the month, shows an icon
 * and the API's one word (Dry, Wet, Heat, Frost, OK), and is coloured by level, so colour never
 * carries the meaning alone. The riskiest month has a thick outline and the word "Riskiest".
 * Arrow keys move between months; the spoken label is the API's own sentence.
 */
defineProps<{
  months: Schemas['MonthRiskOut'][]
  riskiest: number | null
}>()

const selected = defineModel<number | null>({ required: true })

function iconFor(month: Schemas['MonthRiskOut']) {
  return STRESS_TYPES[month.stress_types[0] as StressType]?.icon ?? CircleCheckIcon
}
</script>

<template>
  <ToggleGroup
    type="single"
    :model-value="selected === null ? undefined : String(selected)"
    :aria-label="copy.answer.months"
    class="grid w-full grid-cols-4 gap-2"
    @update:model-value="$event && (selected = Number($event))"
  >
    <ToggleGroupItem
      v-for="month in months"
      :key="month.month"
      :value="String(month.month)"
      class="month-tile"
      :data-level="month.level"
      :data-riskiest="month.month === riskiest"
      :aria-label="month.aria_label"
    >
      <span>{{ monthShort(month.month) }}</span>
      <component
        :is="month.label === 'OK' ? CircleCheckIcon : iconFor(month)"
        class="size-6"
        aria-hidden="true"
      />
      <span>{{ month.label }}</span>
      <span
        v-if="month.month === riskiest"
        class="text-base leading-none"
      >{{ copy.answer.riskiest }}</span>
    </ToggleGroupItem>
  </ToggleGroup>
</template>
