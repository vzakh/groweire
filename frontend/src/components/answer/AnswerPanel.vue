<script setup lang="ts">
import { computed } from 'vue'
import { PencilIcon } from '@lucide/vue'
import Disclaimer from '@/components/common/Disclaimer.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import OptionsSection from '@/components/options/OptionsSection.vue'
import ShareBar from '@/components/share/ShareBar.vue'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { copy } from '@/copy/en'
import type { Schemas } from '@/lib/api'
import { riskCrop } from '@/lib/answers'
import { useCatalogStore } from '@/stores/catalog'
import { useFieldStore } from '@/stores/field'
import { useFlowStore } from '@/stores/flow'
import { useRiskStore } from '@/stores/risk'
import { useRotationsStore } from '@/stores/rotations'
import AreaHistoryCard from './AreaHistoryCard.vue'
import GapList from './GapList.vue'
import MonthDetail from './MonthDetail.vue'
import MonthStrip from './MonthStrip.vue'
import MoreDetail from './MoreDetail.vue'
import SoilCard from './SoilCard.vue'

/**
 * Step 4: the answer. First the API's one sentence, then what we do not know, the month strip
 * (which also drives the map), local proof from satellite, the soil, the rotation options,
 * and print / send. Detail for advisors sits at the end, one tap down.
 */
const flow = useFlowStore()
const field = useFieldStore()
const risk = useRiskStore()
const rotations = useRotationsStore()
const catalog = useCatalogStore()

const cropId = computed(() => riskCrop(flow.answers))
const cropName = computed(() => (cropId.value ? catalog.cropName(cropId.value) : null))

const selectedMonth = computed({
  get: () => risk.selectedMonth,
  set: (month) => month && flow.setMonth(month),
})
const monthDetail = computed(() => risk.answer?.months.find((m) => m.month === risk.selectedMonth) ?? null)

const soilGap = computed(
  () => field.conditions?.information_gaps.find((gap) => gap.code === 'no_soil_test')?.text,
)
/** Gaps about the satellite history: shown when there is no history card to carry them. */
const conditionGaps = computed(() =>
  (field.conditions?.information_gaps ?? []).filter((gap) => gap.code !== 'no_soil_test'),
)

/** Every source behind this answer, once each. */
const provenance = computed(() => {
  const seen = new Map<string, Schemas['Provenance']>()
  for (const list of [risk.answer?.provenance, field.conditions?.provenance, rotations.result?.provenance]) {
    for (const item of list ?? []) if (!seen.has(item.dataset_id)) seen.set(item.dataset_id, item)
  }
  return [...seen.values()]
})

function retryRisk() {
  if (flow.fieldId) risk.predict(flow.fieldId, cropId.value)
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <ErrorState
      v-if="risk.forCropError && !risk.answer"
      :error="risk.forCropError"
      @retry="retryRisk"
    />
    <div
      v-else-if="!risk.answer"
      role="status"
      class="flex flex-col gap-3"
    >
      <h1
        id="panel-title"
        tabindex="-1"
        class="font-heading text-2xl leading-tight font-bold"
      >
        {{ copy.answer.loading }}
      </h1>
      <Skeleton class="h-20" />
      <Skeleton class="h-56" />
    </div>

    <template v-else>
      <!-- The headline is the API's sentence, word for word -->
      <h1
        id="panel-title"
        tabindex="-1"
        data-test="headline"
        class="font-heading text-[1.625rem] leading-tight font-bold text-balance"
      >
        {{ risk.answer.headline }}
      </h1>

      <GapList :gaps="risk.answer.information_gaps" />

      <section
        aria-labelledby="months-title"
        class="flex flex-col gap-3"
      >
        <h2
          id="months-title"
          class="font-heading text-xl font-bold"
        >
          {{ copy.answer.months }}
        </h2>
        <p class="text-base">
          {{ copy.answer.monthHint }}
        </p>
        <MonthStrip
          v-model="selectedMonth"
          :months="risk.answer.months"
          :riskiest="risk.answer.riskiest_month"
        />
        <MonthDetail
          v-if="monthDetail"
          :key="monthDetail.month"
          :month="monthDetail"
          :crop-name="cropName"
          :needs-review="risk.answer.needs_local_review"
        />
      </section>
    </template>

    <!-- Local proof and soil arrive on their own request; the answer does not wait for them -->
    <ErrorState
      v-if="field.conditionsError"
      :error="field.conditionsError"
      @retry="flow.fieldId && field.loadConditions(flow.fieldId)"
    />
    <Skeleton
      v-else-if="!field.conditions"
      class="h-40"
    />
    <template v-else>
      <AreaHistoryCard
        v-if="field.conditions.greenness_history && risk.answer"
        :history="field.conditions.greenness_history"
        :months="risk.answer.months"
      />
      <GapList
        v-if="conditionGaps.length"
        :gaps="conditionGaps"
      />
      <SoilCard
        v-if="field.conditions.soil"
        :soil="field.conditions.soil"
        :gap="soilGap"
      />
    </template>

    <OptionsSection />

    <ShareBar />

    <Button
      variant="outline"
      size="tap"
      @click="flow.goTo(2)"
    >
      <PencilIcon data-icon="inline-start" />
      {{ copy.field.changeAnswers }}
    </Button>

    <MoreDetail
      v-if="field.conditions"
      :conditions="field.conditions"
      :provenance="provenance"
    />

    <Disclaimer />
  </div>
</template>
