<script setup lang="ts">
import { computed } from 'vue'
import { copy } from '@/copy/en'
import { monthName } from '@/lib/format'
import { RISK_LEVELS, STRESS_TYPES, type RiskLevel } from '@/lib/risk'
import { useRiskStore } from '@/stores/risk'

/**
 * What the coloured squares on the map mean: the month and weather type in words, and each
 * level as colour, icon and word together.
 */
/** `inline`: sit in the page under the map (phones), instead of floating over it. */
defineProps<{ inline?: boolean }>()

const risk = useRiskStore()

const view = computed(() => (risk.view?.strength === 'full' ? risk.view : null))
const title = computed(() =>
  view.value
    ? copy.maps.legend(
        monthName(view.value.month),
        view.value.type ? STRESS_TYPES[view.value.type].word.toLowerCase() : copy.maps.legendAll,
      )
    : '',
)
const levels = Object.keys(RISK_LEVELS) as RiskLevel[]
</script>

<template>
  <div
    v-if="view"
    data-test="map-legend"
    class="flex flex-col gap-2"
    :class="
      inline
        ? 'border-b bg-background px-4 py-3'
        : 'pointer-events-none absolute bottom-10 left-3 z-10 max-w-[calc(100%-1.5rem)] rounded-xl bg-background/95 p-3 shadow-md ring-1 ring-foreground/20'
    "
  >
    <p class="text-base font-bold">
      {{ title }}
    </p>
    <ul class="flex flex-wrap gap-2">
      <li
        v-for="level in levels"
        :key="level"
        class="flex items-center gap-1.5 rounded-lg px-2 py-1 text-base font-bold ring-1 ring-foreground/30"
        :class="RISK_LEVELS[level].class"
      >
        <component
          :is="RISK_LEVELS[level].icon"
          class="size-5"
          aria-hidden="true"
        />
        {{ RISK_LEVELS[level].word }}
      </li>
    </ul>
  </div>
</template>
