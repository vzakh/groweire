<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ChevronDownIcon, CircleHelpIcon, EyeIcon } from '@lucide/vue'
import CropIcon from '@/components/common/CropIcon.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Skeleton } from '@/components/ui/skeleton'
import { copy } from '@/copy/en'
import { YEARS } from '@/lib/query'
import { useCatalogStore } from '@/stores/catalog'
import { useFlowStore } from '@/stores/flow'
import { useRiskStore } from '@/stores/risk'

/**
 * Step 2: what grew here. Last year is the one question that must be answered; earlier years
 * are behind one tap, with "Same as last year" and "Not sure" as shortcuts.
 */
const flow = useFlowStore()
const catalog = useCatalogStore()
const risk = useRiskStore()

// Open the earlier years straight away when a shared link already has them
const earlierOpen = ref(flow.answers.crops.slice(1).some(Boolean))
const earlierYears = Array.from({ length: YEARS - 1 }, (_, i) => i + 1)

function setCrop(year: number, id: string | null) {
  const crops = [...flow.answers.crops]
  // Tapping the picked crop of an earlier year clears it; last year always keeps an answer
  crops[year] = year > 0 && crops[year] === id ? null : id
  flow.setAnswers({ crops })
}

onMounted(() => {
  catalog.loadCrops()
  flow.setGuard(() => (flow.answers.crops[0] ? true : copy.crops.needLast))
})
onBeforeUnmount(() => flow.setGuard(null))
</script>

<template>
  <div class="flex flex-col gap-5">
    <h1
      id="panel-title"
      tabindex="-1"
      class="font-heading text-2xl leading-tight font-bold text-balance"
    >
      {{ copy.steps[1].title }}
    </h1>

    <!-- The answer starts to arrive while the farmer is still choosing: the API's own sentence -->
    <Alert v-if="risk.generalAnswer">
      <EyeIcon aria-hidden="true" />
      <AlertTitle class="text-base font-bold">
        {{ copy.crops.firstLook }}
      </AlertTitle>
      <AlertDescription class="text-base text-foreground">
        {{ risk.generalAnswer.headline }}
      </AlertDescription>
    </Alert>

    <ErrorState
      v-if="catalog.cropsError"
      :error="catalog.cropsError"
      @retry="catalog.loadCrops()"
    />
    <div
      v-else-if="!catalog.mainCrops.length"
      class="grid grid-cols-3 gap-2"
      role="status"
      :aria-label="copy.loading"
    >
      <Skeleton
        v-for="n in 9"
        :key="n"
        class="h-24"
      />
    </div>

    <template v-else>
      <fieldset>
        <legend class="mb-2 text-lg font-bold">
          {{ copy.crops.years[0] }}
        </legend>
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="crop in catalog.mainCrops"
            :key="crop.id"
            type="button"
            class="tile"
            :aria-pressed="flow.answers.crops[0] === crop.id"
            @click="setCrop(0, crop.id)"
          >
            <CropIcon
              :family="crop.family"
              class="size-7"
            />
            <span>{{ crop.name }}</span>
          </button>
        </div>
      </fieldset>

      <Collapsible v-model:open="earlierOpen">
        <CollapsibleTrigger as-child>
          <Button
            variant="outline"
            size="tap"
            class="w-full justify-between"
          >
            {{ copy.crops.earlier }}
            <ChevronDownIcon
              data-icon="inline-end"
              :class="{ 'rotate-180': earlierOpen }"
            />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent class="flex flex-col gap-5 pt-4">
          <p class="text-base text-muted-foreground">
            {{ copy.crops.earlierHint }}
          </p>
          <fieldset
            v-for="year in earlierYears"
            :key="year"
          >
            <legend class="mb-2 text-lg font-bold">
              {{ copy.crops.years[year] }}
            </legend>
            <div class="mb-2 flex flex-wrap gap-2">
              <button
                type="button"
                class="chip"
                :disabled="!flow.answers.crops[0]"
                :aria-pressed="!!flow.answers.crops[0] && flow.answers.crops[year] === flow.answers.crops[0]"
                @click="setCrop(year, flow.answers.crops[0])"
              >
                {{ copy.crops.sameAsLast }}
              </button>
              <button
                type="button"
                class="chip"
                @click="setCrop(year, null)"
              >
                <CircleHelpIcon
                  class="size-5"
                  aria-hidden="true"
                />
                {{ copy.crops.notSure }}
              </button>
            </div>
            <div class="grid grid-cols-3 gap-2">
              <button
                v-for="crop in catalog.mainCrops"
                :key="crop.id"
                type="button"
                class="tile"
                :aria-pressed="flow.answers.crops[year] === crop.id"
                @click="setCrop(year, crop.id)"
              >
                <CropIcon
                  :family="crop.family"
                  class="size-7"
                />
                <span>{{ crop.name }}</span>
              </button>
            </div>
          </fieldset>
        </CollapsibleContent>
      </Collapsible>
    </template>
  </div>
</template>
