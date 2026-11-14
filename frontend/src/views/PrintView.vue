<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowLeftIcon, PrinterIcon } from '@lucide/vue'
import ErrorState from '@/components/common/ErrorState.vue'
import { Button } from '@/components/ui/button'
import { copy } from '@/copy/en'
import { riskCrop } from '@/lib/answers'
import { hectares, humanise, monthName } from '@/lib/format'
import { RISK_LEVELS } from '@/lib/risk'
import { router } from '@/router'
import { useCatalogStore } from '@/stores/catalog'
import { useFieldStore } from '@/stores/field'
import { useFlowStore } from '@/stores/flow'
import { useRiskStore } from '@/stores/risk'
import { useRotationsStore } from '@/stores/rotations'

/**
 * The one-page summary to bring to the advisor: A4, readable in black and white, no map tiles.
 * It holds the field, the answer sentence, the months as a word table, the same-crop note,
 * three rotations with why, rule check and advisor questions, the local satellite line,
 * what we do not know, the sources and the "you decide" line.
 */
const flow = useFlowStore()
const field = useFieldStore()
const risk = useRiskStore()
const rotations = useRotationsStore()
const catalog = useCatalogStore()

const cropId = computed(() => riskCrop(flow.answers))

onMounted(async () => {
  const id = flow.fieldId
  if (!id) return
  catalog.loadCrops()
  await field.ensure(id)
  if (field.field?.field_id !== id) return
  field.loadConditions(id)
  risk.predict(id, cropId.value)
  rotations.compare()
})

const answer = computed(() => risk.answer ?? (cropId.value ? null : risk.generalAnswer))
const strategies = computed(() => {
  const all = rotations.result?.strategies ?? []
  return [...all.filter((s) => s.is_current), ...all.filter((s) => !s.is_current)].slice(0, 3)
})
const ready = computed(() => !!field.field && !!answer.value && !!field.conditions && (!!rotations.result || !rotations.body))
const failed = computed(() => field.fieldError ?? risk.forCropError ?? rotations.error ?? field.conditionsError)

const gaps = computed(() => {
  const seen = new Map<string, string>()
  for (const gap of [...(answer.value?.information_gaps ?? []), ...(field.conditions?.information_gaps ?? [])]) {
    seen.set(gap.code, gap.text)
  }
  return [...seen.values()]
})
const sources = computed(() => {
  const seen = new Map<string, string>()
  for (const item of [...(answer.value?.provenance ?? []), ...(rotations.result?.provenance ?? [])]) {
    // Paper has little room: the name of the source without its bracketed detail
    seen.set(item.dataset_id, item.description.split(/ \(|, /)[0]!)
  }
  return [...seen.values()]
})

/** Questions per option on paper; the screen shows them all. */
const PRINT_QUESTIONS = 2

/** March to June, and July to October. */
const monthHalves = computed(() => {
  const months = answer.value?.months ?? []
  const middle = Math.ceil(months.length / 2)
  return [months.slice(0, middle), months.slice(middle)]
})

const today = new Date().toLocaleDateString('en-IE', { day: 'numeric', month: 'long', year: 'numeric' })
const backTo = computed(() => flow.place({ step: 4, section: null }))
const shareUrl = computed(() => new URL(router.resolve(backTo.value).href, location.origin).href)

/** The field's outline as a small drawing: no map tiles on paper. */
const outline = computed(() => {
  const ring = (field.field?.geometry as { coordinates?: number[][][] } | undefined)?.coordinates?.[0]
  if (!ring?.length) return null
  const xs = ring.map((p) => p[0]!)
  const ys = ring.map((p) => p[1]!)
  const [minX, maxX, minY, maxY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]
  // Degrees of longitude are shorter than degrees of latitude this far north
  const squeeze = Math.cos((((minY + maxY) / 2) * Math.PI) / 180)
  const scale = 90 / Math.max((maxX - minX) * squeeze, maxY - minY || 1e-9)
  return ring
    .map((p) => `${(5 + (p[0]! - minX) * squeeze * scale).toFixed(1)},${(95 - (p[1]! - minY) * scale).toFixed(1)}`)
    .join(' ')
})

const nameOf = (id: string) => catalog.cropById.get(id)?.name ?? humanise(id)

function print() {
  window.print()
}

// Open the print dialog once, when everything is on the page
const printed = ref(false)
watch(ready, async (isReady) => {
  if (!isReady || printed.value) return
  printed.value = true
  await nextTick()
  print()
})
</script>

<template>
  <main class="print-page mx-auto flex max-w-[50rem] flex-col gap-4 bg-white p-6 text-black">
    <div class="flex flex-wrap gap-2 print:hidden">
      <Button
        as-child
        variant="outline"
        size="tap"
      >
        <RouterLink :to="backTo">
          <ArrowLeftIcon data-icon="inline-start" />
          {{ copy.print.back }}
        </RouterLink>
      </Button>
      <Button
        size="tap"
        :disabled="!ready"
        @click="print"
      >
        <PrinterIcon data-icon="inline-start" />
        {{ copy.share.print }}
      </Button>
    </div>

    <ErrorState
      v-if="failed && !ready"
      :error="failed"
      action=""
    />
    <p
      v-else-if="!ready"
      role="status"
      class="text-lg"
    >
      {{ copy.answer.loading }}
    </p>

    <template v-else-if="field.field && answer">
      <header class="flex items-start justify-between gap-4 border-b-2 border-black pb-3">
        <div>
          <p class="font-heading text-2xl font-bold">
            {{ copy.brand }} · {{ copy.print.title }}
          </p>
          <p>
            {{ copy.field.summary(field.field.name, hectares(field.field.area_ha)) }} ·
            {{ copy.print.date(today) }}
          </p>
        </div>
        <svg
          v-if="outline"
          viewBox="0 0 100 100"
          class="size-14 shrink-0"
          aria-hidden="true"
        >
          <polygon
            :points="outline"
            fill="none"
            stroke="black"
            stroke-width="2.5"
          />
        </svg>
      </header>

      <h1
        data-test="print-headline"
        class="font-heading text-2xl leading-tight font-bold"
      >
        {{ answer.headline }}
      </h1>

      <!-- Two short tables side by side, so the page stays on one sheet -->
      <div class="grid grid-cols-2 gap-x-5">
        <table
          v-for="(half, index) in monthHalves"
          :key="index"
          class="w-full border-collapse self-start text-left"
        >
          <thead>
            <tr class="border-b-2 border-black">
              <th class="py-0.5 pr-2">
                {{ copy.print.monthTable.month }}
              </th>
              <th class="py-0.5 pr-2">
                {{ copy.print.monthTable.word }}
              </th>
              <th class="py-0.5">
                {{ copy.print.monthTable.how }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="m in half"
              :key="m.month"
              class="border-b border-black/40"
              :class="{ 'font-bold': m.month === answer.riskiest_month }"
            >
              <td class="py-0.5 pr-2 whitespace-nowrap">
                {{ monthName(m.month) }}
              </td>
              <td class="py-0.5 pr-2">
                {{ m.label }} ({{ RISK_LEVELS[m.level].word.toLowerCase() }})
              </td>
              <td class="py-0.5 whitespace-nowrap">
                {{ m.frequency_text }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p v-if="field.conditions?.greenness_history">
        {{ field.conditions.greenness_history.text }}
      </p>

      <p
        v-if="rotations.result?.same_crop_note"
        class="border-l-4 border-black pl-3"
      >
        {{ rotations.result.same_crop_note.text }}
      </p>

      <div class="grid grid-cols-3 gap-5 border-t-2 border-black pt-3">
      <section
        v-for="strategy in strategies"
        :key="strategy.id"
        class="break-inside-avoid"
      >
        <h2 class="font-heading text-xl font-bold">
          {{ strategy.headline }}
        </h2>
        <p>{{ strategy.sequence.map(nameOf).join(' → ') }}</p>
        <p>{{ strategy.one_line_why }}</p>
        <p class="font-bold">
          {{
            strategy.metrics.rule_compliance.ie_crop_rotation_2_of_4
              ? copy.options.rules.ok
              : copy.options.rules.check
          }}
        </p>
        <p class="mt-1 font-bold">
          {{ copy.options.ask }}
        </p>
        <ul class="list-disc pl-5">
          <li
            v-for="question in strategy.advisor_questions.slice(0, PRINT_QUESTIONS)"
            :key="question"
          >
            {{ question }}
          </li>
        </ul>
      </section>
      </div>

      <!-- What we do not know, next to the sources: side by side to stay on one sheet -->
      <div class="grid grid-cols-2 gap-5 border-t-2 border-black pt-3">
        <section v-if="gaps.length">
          <h2 class="font-bold">
            {{ copy.answer.gaps }}
          </h2>
          <ul class="list-disc pl-5">
            <li
              v-for="gap in gaps"
              :key="gap"
            >
              {{ gap }}
            </li>
          </ul>
        </section>
        <footer>
          <p class="font-bold">
            {{ copy.disclaimer }}
          </p>
          <p>{{ copy.answer.sources }}: {{ sources.join('; ') }}.</p>
        </footer>
      </div>
      <p class="break-all">
        {{ copy.print.link }} {{ shareUrl }}
      </p>
    </template>
  </main>
</template>
