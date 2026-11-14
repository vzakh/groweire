<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronDownIcon } from '@lucide/vue'
import TermHelp from '@/components/common/TermHelp.vue'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { copy } from '@/copy/en'
import type { Schemas } from '@/lib/api'
import { monthShort } from '@/lib/format'

/**
 * For advisors and judges, one tap below the answer: normal weather by month (rain next to
 * "the weather's thirst", frost and hot days), how it has changed, the monthly satellite
 * greenness, and every source. Nothing here is needed to read the answer.
 */
const props = defineProps<{
  conditions: Schemas['ConditionsOut']
  provenance: Schemas['Provenance'][]
}>()

const open = ref(false)

// --- climate: rain vs thirst per month ------------------------------------------------
const CHART_H = 80
const months = computed(() => props.conditions.climate?.months ?? [])
const climateBars = computed(() => {
  const top = Math.max(1, ...months.value.flatMap((m) => [m.precip_mm ?? 0, m.et0_mm ?? 0]))
  return months.value.map((m, index) => ({
    month: m.month,
    x: index * 20,
    rain: ((m.precip_mm ?? 0) / top) * CHART_H,
    thirst: ((m.et0_mm ?? 0) / top) * CHART_H,
  }))
})

// --- trends -----------------------------------------------------------------------------
const trendLines = computed(() => {
  const trends = props.conditions.trends
  if (!trends) return []
  const t = copy.answer.trends
  const signed = (value: number, digits: number) =>
    `${Math.abs(value).toFixed(digits)} ${value > 0 ? t.more : t.less}`
  const lines: string[] = []
  if (trends.precip_mm_per_decade) lines.push(t.rain(signed(trends.precip_mm_per_decade, 1), trends.n_years))
  if (trends.tmax_c_per_decade) lines.push(t.tmax(signed(trends.tmax_c_per_decade, 1)))
  if (trends.frost_days_per_decade) lines.push(t.frost(signed(trends.frost_days_per_decade, 1)))
  return lines
})

// --- monthly greenness --------------------------------------------------------------------
const SERIES_H = 50
const series = computed(() => {
  const data = props.conditions.series
  if (!data || !data.ndvi.some((v) => v !== null)) return null
  const bars = data.ndvi.map((value, index) => ({
    x: index * 3,
    height: value === null ? 0 : Math.max(1, value * SERIES_H),
  }))
  return {
    bars,
    width: data.ndvi.length * 3,
    text: copy.answer.series.text(data.months[0] ?? '', data.months[data.months.length - 1] ?? ''),
  }
})
</script>

<template>
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
    <CollapsibleContent class="flex flex-col gap-6 pt-4">
      <section
        v-if="conditions.climate"
        class="flex flex-col gap-3"
      >
        <h3 class="font-heading text-xl font-bold">
          {{ copy.answer.climate.title }}
        </h3>
        <p class="text-base">
          {{ copy.answer.climate.period(conditions.climate.period) }}
        </p>
        <svg
          :viewBox="`0 0 ${climateBars.length * 20} ${CHART_H}`"
          class="w-full"
          aria-hidden="true"
        >
          <g
            v-for="bar in climateBars"
            :key="bar.month"
          >
            <rect
              :x="bar.x + 2"
              :y="CHART_H - bar.rain"
              width="7"
              :height="bar.rain"
              class="fill-atlantic"
            />
            <rect
              :x="bar.x + 10"
              :y="CHART_H - bar.thirst"
              width="7"
              :height="bar.thirst"
              class="fill-gold stroke-foreground"
              stroke-width="0.5"
            />
          </g>
        </svg>
        <div
          class="grid text-center text-base"
          :style="{ gridTemplateColumns: `repeat(${climateBars.length}, 1fr)` }"
          aria-hidden="true"
        >
          <span
            v-for="bar in climateBars"
            :key="bar.month"
          >{{ monthShort(bar.month).charAt(0) }}</span>
        </div>
        <ul class="flex flex-wrap gap-x-5 gap-y-1 text-base">
          <li class="flex items-center gap-2">
            <span
              class="inline-block size-4 bg-atlantic"
              aria-hidden="true"
            />{{ copy.answer.climate.rain }}
          </li>
          <li class="flex items-center gap-2">
            <span
              class="inline-block size-4 border border-foreground bg-gold"
              aria-hidden="true"
            />{{ copy.answer.climate.thirst }}
          </li>
        </ul>
        <TermHelp term="evapotranspiration" />
        <div class="overflow-x-auto">
          <table class="w-full text-left text-base">
            <thead>
              <tr class="border-b-2 border-foreground">
                <th class="py-1 pr-2">
                  {{ copy.answer.climate.month }}
                </th>
                <th class="py-1 pr-2">
                  {{ copy.answer.climate.rain }}
                </th>
                <th class="py-1 pr-2">
                  {{ copy.answer.climate.thirst }}
                </th>
                <th class="py-1 pr-2">
                  {{ copy.answer.climate.frost }}
                </th>
                <th class="py-1">
                  {{ copy.answer.climate.hot }}
                </th>
              </tr>
            </thead>
            <tbody class="tabular-nums">
              <tr
                v-for="m in months"
                :key="m.month"
                class="border-b"
              >
                <th class="py-1 pr-2 font-bold">
                  {{ monthShort(m.month) }}
                </th>
                <td class="py-1 pr-2">
                  {{ m.precip_mm === null ? '–' : Math.round(m.precip_mm) }}
                </td>
                <td class="py-1 pr-2">
                  {{ m.et0_mm === null ? '–' : Math.round(m.et0_mm) }}
                </td>
                <td class="py-1 pr-2">
                  {{ m.frost_days ?? '–' }}
                </td>
                <td class="py-1">
                  {{ m.hot_days ?? '–' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section
        v-if="trendLines.length"
        class="flex flex-col gap-2"
      >
        <h3 class="font-heading text-xl font-bold">
          {{ copy.answer.trends.title }}
        </h3>
        <p
          v-for="line in trendLines"
          :key="line"
          class="text-base"
        >
          {{ line }}
        </p>
      </section>

      <section
        v-if="series"
        class="flex flex-col gap-2"
      >
        <h3 class="font-heading text-xl font-bold">
          {{ copy.answer.series.title }}
        </h3>
        <svg
          :viewBox="`0 0 ${series.width} ${SERIES_H}`"
          class="w-full"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <rect
            v-for="bar in series.bars"
            :key="bar.x"
            :x="bar.x"
            :y="SERIES_H - bar.height"
            width="2.2"
            :height="bar.height"
            class="fill-foreground/60"
          />
        </svg>
        <p class="text-base">
          {{ series.text }}
        </p>
      </section>

      <section
        v-if="provenance.length"
        class="flex flex-col gap-2"
      >
        <h3 class="font-heading text-xl font-bold">
          {{ copy.answer.sources }}
        </h3>
        <ul class="flex list-disc flex-col gap-1 pl-5 text-base">
          <li
            v-for="item in provenance"
            :key="item.dataset_id"
          >
            <a
              :href="item.url"
              target="_blank"
              rel="noopener"
              class="underline underline-offset-4"
            >{{ item.description }}</a>
          </li>
        </ul>
      </section>
    </CollapsibleContent>
  </Collapsible>
</template>
