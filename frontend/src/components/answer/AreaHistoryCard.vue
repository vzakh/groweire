<script setup lang="ts">
import { computed } from 'vue'
import TermHelp from '@/components/common/TermHelp.vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { copy } from '@/copy/en'
import type { Schemas } from '@/lib/api'
import { listWords, monthName } from '@/lib/format'

/**
 * Local proof: how green the land around the field was each summer, seen by satellite.
 * The sentence is the API's. The chart marks the least green summers, and where one of those
 * years was also counted as a dry month in the risk counts, a line joins the two.
 */
const props = defineProps<{
  history: Schemas['GreennessHistory']
  /** Months of the field's answer, to find years that were also counted as dry. */
  months: Schemas['MonthRiskOut'][]
}>()

const BAR = 10
const GAP = 3
const HEIGHT = 60

const bars = computed(() => {
  const values = props.history.summer_ndvi.filter((v): v is number => v !== null)
  const low = Math.min(...values)
  const high = Math.max(...values)
  // Summers differ by a few hundredths, so the bars span the range seen here, not zero to one
  const span = high - low || 1
  return props.history.years.map((year, index) => {
    const value = props.history.summer_ndvi[index]
    const height = value == null ? 0 : 12 + ((value - low) / span) * (HEIGHT - 12)
    return {
      year,
      x: index * (BAR + GAP),
      height,
      y: HEIGHT - height,
      lowest: props.history.lowest_years.includes(year),
    }
  })
})

const width = computed(() => props.history.years.length * (BAR + GAP) - GAP)

/** "2018 was also counted as a dry July here." for each least-green year that matches. */
const alsoDry = computed(() => {
  const lines: string[] = []
  for (const year of props.history.lowest_years) {
    const month = props.months.find((m) =>
      m.counts.some((c) => c.stress_type === 'drought' && c.example_years.includes(year)),
    )
    if (month) lines.push(copy.answer.area.also(year, monthName(month.month)))
  }
  return lines
})
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle class="font-heading text-xl font-bold">
        {{ copy.answer.area.title(history.years[0]!, history.years[history.years.length - 1]!) }}
      </CardTitle>
    </CardHeader>
    <CardContent class="flex flex-col gap-3">
      <p
        data-test="area-text"
        class="text-base"
      >
        {{ history.text }}
      </p>
      <svg
        :viewBox="`0 0 ${width} ${HEIGHT}`"
        class="w-full"
        role="img"
        :aria-label="copy.answer.area.chart"
      >
        <g
          v-for="bar in bars"
          :key="bar.year"
        >
          <rect
            :x="bar.x"
            :y="bar.y"
            :width="BAR"
            :height="bar.height"
            rx="1.5"
            :class="bar.lowest ? 'fill-foreground' : 'fill-foreground/25'"
          />
        </g>
      </svg>
      <p class="flex items-center gap-2 text-base">
        <span
          class="inline-block size-4 rounded-sm bg-foreground"
          aria-hidden="true"
        />
        {{ copy.answer.area.lowest }}: {{ listWords(history.lowest_years) }}
      </p>
      <p
        v-for="line in alsoDry"
        :key="line"
        class="text-base font-bold"
      >
        {{ line }}
      </p>
      <TermHelp term="ndvi" />
    </CardContent>
  </Card>
</template>
