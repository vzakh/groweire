<script setup lang="ts">
import { computed, onMounted } from 'vue'
import GapList from '@/components/answer/GapList.vue'
import { copy } from '@/copy/en'
import type { Schemas } from '@/lib/api'
import { useCatalogStore } from '@/stores/catalog'
import { useFieldStore } from '@/stores/field'
import { useRiskStore } from '@/stores/risk'
import { useRotationsStore } from '@/stores/rotations'

/**
 * "Data and sources": how the risk is counted, in six plain sentences, then every data source
 * the API named in its answers for this field, and everything it said it does not know.
 */
const catalog = useCatalogStore()
const field = useFieldStore()
const risk = useRiskStore()
const rotations = useRotationsStore()

onMounted(() => catalog.loadCrops())

const responses = computed(() => [
  risk.answer ?? risk.generalAnswer,
  field.conditions,
  rotations.result,
  catalog.crops,
])

const provenance = computed(() => {
  const seen = new Map<string, Schemas['Provenance']>()
  for (const response of responses.value) {
    for (const item of response?.provenance ?? []) if (!seen.has(item.dataset_id)) seen.set(item.dataset_id, item)
  }
  return [...seen.values()]
})

const gaps = computed(() => {
  const seen = new Map<string, Schemas['InformationGap']>()
  for (const response of [risk.answer ?? risk.generalAnswer, field.conditions, rotations.result]) {
    for (const gap of response?.information_gaps ?? []) if (!seen.has(gap.code)) seen.set(gap.code, gap)
  }
  return [...seen.values()]
})
</script>

<template>
  <div class="flex flex-col gap-6">
    <h1
      id="panel-title"
      tabindex="-1"
      class="font-heading text-2xl leading-tight font-bold text-balance"
    >
      {{ copy.more.sources.label }}
    </h1>

    <section class="flex flex-col gap-2">
      <h2 class="font-heading text-xl font-bold">
        {{ copy.sourcesPage.howTitle }}
      </h2>
      <ol class="flex list-decimal flex-col gap-2 pl-6 text-base">
        <li
          v-for="line in copy.sourcesPage.how"
          :key="line"
        >
          {{ line }}
        </li>
      </ol>
    </section>

    <GapList :gaps="gaps" />

    <section class="flex flex-col gap-2">
      <h2 class="font-heading text-xl font-bold">
        {{ copy.sourcesPage.dataTitle }}
      </h2>
      <ul class="flex flex-col gap-3">
        <li
          v-for="item in provenance"
          :key="item.dataset_id"
          data-test="source"
          class="text-base"
        >
          <a
            :href="item.url"
            target="_blank"
            rel="noopener"
            class="font-bold underline underline-offset-4"
          >{{ item.description }}</a>
          <span v-if="item.period"> · {{ item.period }}</span>
        </li>
      </ul>
      <p
        v-if="!field.conditions"
        class="text-base"
      >
        {{ copy.sourcesPage.dataHint }}
      </p>
    </section>
  </div>
</template>
