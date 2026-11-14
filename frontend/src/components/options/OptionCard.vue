<script setup lang="ts">
import { computed, ref, type Component } from 'vue'
import {
  ChevronDownIcon,
  CircleAlertIcon,
  CircleCheckIcon,
  CloudSunIcon,
  LayersIcon,
  ShovelIcon,
} from '@lucide/vue'
import CropIcon from '@/components/common/CropIcon.vue'
import Disclaimer from '@/components/common/Disclaimer.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { copy } from '@/copy/en'
import type { Schemas } from '@/lib/api'
import { humanise } from '@/lib/format'

/**
 * One rotation, as one card. Face: the API's headline and one-line why, the four years as crop
 * pictures (with winter cover crops between), three icon-and-word comparisons with the current
 * rotation, and the crop-rule chip. One tap opens the five explanation blocks. Every card ends
 * with questions for the advisor and the "you decide" line. Scores never show as numbers.
 */
const props = defineProps<{
  strategy: Schemas['Strategy']
  /** Crop catalogue, to turn ids into names and pictures. */
  crops: Map<string, Schemas['CropOut']>
  /** Sources from the same response, to link evidence to where it comes from. */
  provenance: Schemas['Provenance'][]
  /** The weights the ranking used, most important first when sorted. */
  weights: Record<string, number>
}>()

const whyOpen = ref(false)
const detailOpen = ref(false)

const nameOf = (id: string) => props.crops.get(id)?.name ?? humanise(id)

const years = computed(() =>
  props.strategy.sequence.map((id, index) => ({
    year: index + 1,
    id,
    cover: props.strategy.cover_crops.find((cover) => cover.after_year === index + 1)?.crop_id ?? null,
  })),
)

const compare = computed(() => {
  const vs = props.strategy.vs_current
  if (!vs) return []
  const words = copy.options.vs
  const rows: { key: string; icon: Component; label: string; word: string }[] = [
    { key: 'risk', icon: CloudSunIcon, label: words.risk.label, word: words.risk[vs.risk] },
    { key: 'bare_soil', icon: LayersIcon, label: words.bare_soil.label, word: words.bare_soil[vs.bare_soil] },
    { key: 'workload', icon: ShovelIcon, label: words.workload.label, word: words.workload[vs.workload] },
  ]
  return rows
})

const rules = computed(() => props.strategy.metrics.rule_compliance)

const sourceUrl = (id: string) => props.provenance.find((item) => item.dataset_id === id)?.url

const criteria = computed(() =>
  Object.entries(props.strategy.criteria)
    .filter(([key]) => copy.options.criteria[key])
    .map(([key, value]) => ({ key, label: copy.options.criteria[key]!, width: `${Math.round(value * 100)}%` })),
)

const rankedBy = computed(() => {
  const sorted = Object.entries(props.weights)
    .filter(([key, weight]) => weight > 0 && copy.options.criteria[key])
    .sort((a, b) => b[1] - a[1])
  if (!sorted.length) return null
  const labels = sorted.map(([key], index) =>
    index === 0 ? `${copy.options.criteria[key]} (${copy.options.most})` : copy.options.criteria[key]!,
  )
  return copy.options.rankedBy(labels.join(', '))
})

const metricLines = computed(() => {
  const m = props.strategy.metrics
  const lines = [copy.options.metrics.bare(String(Math.round(m.bare_months_per_year * 10) / 10))]
  if (m.water_demand_mm !== null) lines.push(copy.options.metrics.water(Math.round(m.water_demand_mm)))
  if (m.n_fixing_years > 0) lines.push(copy.options.metrics.nitrogen(m.n_fixing_years))
  return lines
})
</script>

<template>
  <Card :data-test="`option-${strategy.id}`">
    <CardHeader class="gap-2">
      <Badge
        v-if="strategy.is_current"
        variant="secondary"
        class="h-auto px-3 py-1 text-base font-bold"
      >
        {{ copy.options.yours }}
      </Badge>
      <CardTitle
        data-test="option-headline"
        class="font-heading text-[1.375rem] leading-tight font-bold text-balance"
      >
        {{ strategy.headline }}
      </CardTitle>
      <p class="text-base">
        {{ strategy.one_line_why }}
      </p>
    </CardHeader>

    <CardContent class="flex flex-col gap-4">
      <!-- The four years, with what covers the soil over winter -->
      <ol class="grid grid-cols-2 gap-2">
        <li
          v-for="item in years"
          :key="item.year"
          class="flex flex-col gap-1 rounded-lg bg-muted p-2 text-base"
        >
          <span class="font-bold">{{ copy.options.year(item.year) }}</span>
          <span class="flex items-center gap-2">
            <CropIcon
              :family="crops.get(item.id)?.family"
              class="size-5 shrink-0"
            />
            {{ nameOf(item.id) }}
          </span>
          <span
            v-if="item.cover"
            class="text-muted-foreground"
          >{{ copy.options.coverAfter }}: {{ nameOf(item.cover) }}</span>
        </li>
      </ol>

      <!-- Against the current rotation: icon and word, never colour alone -->
      <p
        v-if="strategy.is_current"
        class="text-base"
      >
        {{ copy.options.startingPoint }}
      </p>
      <ul
        v-else
        data-test="vs-current"
        class="flex flex-col gap-1"
      >
        <li
          v-for="row in compare"
          :key="row.key"
          class="flex items-center gap-2 text-base"
        >
          <component
            :is="row.icon"
            class="size-5 shrink-0"
            aria-hidden="true"
          />
          <span>{{ row.label }}: <strong>{{ row.word }}</strong></span>
        </li>
      </ul>

      <div class="flex flex-col gap-1">
        <Badge
          data-test="rule-chip"
          variant="outline"
          class="h-auto gap-2 px-3 py-1 text-base font-bold whitespace-normal"
        >
          <!-- Wrapped, because the badge shrinks icons that are its direct children -->
          <span class="flex">
            <component
              :is="rules.ie_crop_rotation_2_of_4 ? CircleCheckIcon : CircleAlertIcon"
              class="size-5"
              aria-hidden="true"
            />
          </span>
          {{ rules.ie_crop_rotation_2_of_4 ? copy.options.rules.ok : copy.options.rules.check }}
        </Badge>
        <p
          v-if="rules.two_crop_rule_10_30ha == null"
          data-test="rule-unknown"
          class="text-base text-muted-foreground"
        >
          {{ copy.options.rules.unknown }}
        </p>
      </div>

      <Collapsible v-model:open="whyOpen">
        <CollapsibleTrigger as-child>
          <Button
            variant="outline"
            size="tap"
            class="w-full justify-between"
          >
            {{ copy.options.why }}
            <ChevronDownIcon
              data-icon="inline-end"
              :class="{ 'rotate-180': whyOpen }"
            />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent
          data-test="why-blocks"
          class="flex flex-col gap-4 pt-4"
        >
          <section>
            <h4 class="text-base font-bold">
              {{ copy.options.blocks.why }}
            </h4>
            <p class="text-base">
              {{ strategy.explanation.why_suggested }}
            </p>
          </section>
          <section v-if="strategy.explanation.evidence.length">
            <h4 class="text-base font-bold">
              {{ copy.options.blocks.evidence }}
            </h4>
            <ul class="flex list-disc flex-col gap-1 pl-5 text-base">
              <li
                v-for="item in strategy.explanation.evidence"
                :key="item.claim"
              >
                {{ item.claim }}
                <a
                  v-if="sourceUrl(item.source)"
                  :href="sourceUrl(item.source)"
                  target="_blank"
                  rel="noopener"
                  class="underline underline-offset-4"
                >({{ copy.source }}: {{ humanise(item.source) }})</a>
                <span v-else>({{ copy.source }}: {{ humanise(item.source) }})</span>
              </li>
            </ul>
          </section>
          <section v-if="strategy.explanation.benefits.length">
            <h4 class="text-base font-bold">
              {{ copy.options.blocks.benefits }}
            </h4>
            <ul class="flex list-disc flex-col gap-1 pl-5 text-base">
              <li
                v-for="item in strategy.explanation.benefits"
                :key="item"
              >
                {{ item }}
              </li>
            </ul>
          </section>
          <section v-if="strategy.explanation.information_gaps.length">
            <h4 class="text-base font-bold">
              {{ copy.options.blocks.gaps }}
            </h4>
            <ul class="flex list-disc flex-col gap-1 pl-5 text-base">
              <li
                v-for="item in strategy.explanation.information_gaps"
                :key="item"
              >
                {{ item }}
              </li>
            </ul>
          </section>
          <section v-if="strategy.explanation.risks_needing_local_review.length">
            <h4 class="text-base font-bold">
              {{ copy.options.blocks.check }}
            </h4>
            <ul class="flex list-disc flex-col gap-1 pl-5 text-base">
              <li
                v-for="item in strategy.explanation.risks_needing_local_review"
                :key="item"
              >
                {{ item }}
              </li>
            </ul>
          </section>
        </CollapsibleContent>
      </Collapsible>

      <section
        v-if="strategy.advisor_questions.length"
        data-test="advisor-questions"
      >
        <h4 class="text-base font-bold">
          {{ copy.options.ask }}
        </h4>
        <ul class="flex list-disc flex-col gap-1 pl-5 text-base">
          <li
            v-for="question in strategy.advisor_questions"
            :key="question"
          >
            {{ question }}
          </li>
        </ul>
      </section>

      <Collapsible v-model:open="detailOpen">
        <CollapsibleTrigger as-child>
          <Button
            variant="outline"
            size="tap"
            class="w-full justify-between"
          >
            {{ copy.moreDetail }}
            <ChevronDownIcon
              data-icon="inline-end"
              :class="{ 'rotate-180': detailOpen }"
            />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent class="flex flex-col gap-3 pt-4">
          <h4 class="text-base font-bold">
            {{ copy.options.criteriaTitle }}
          </h4>
          <ul class="flex flex-col gap-2">
            <li
              v-for="item in criteria"
              :key="item.key"
              class="text-base"
            >
              <span>{{ item.label }}</span>
              <div
                class="mt-1 h-3 rounded-full bg-muted ring-1 ring-foreground/30"
                aria-hidden="true"
              >
                <div
                  class="h-full rounded-full bg-foreground"
                  :style="{ width: item.width }"
                />
              </div>
            </li>
          </ul>
          <p class="text-base text-muted-foreground">
            {{ copy.options.criteriaScale }}
          </p>
          <p
            v-for="line in metricLines"
            :key="line"
            class="text-base"
          >
            {{ line }}
          </p>
          <p
            v-if="rankedBy"
            class="text-base"
          >
            {{ rankedBy }}
          </p>
        </CollapsibleContent>
      </Collapsible>

      <Disclaimer />
    </CardContent>
  </Card>
</template>
