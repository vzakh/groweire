<script setup lang="ts">
import { computed, onMounted, ref, type Component } from 'vue'
import {
  BeanIcon,
  BeefIcon,
  BugOffIcon,
  ClockIcon,
  CoinsIcon,
  DropletIcon,
  LayersIcon,
  StoreIcon,
} from '@lucide/vue'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { copy } from '@/copy/en'
import { togglePriority } from '@/lib/answers'
import { humanise } from '@/lib/format'
import { PRIORITIES, type Priority } from '@/lib/query'
import { useCatalogStore } from '@/stores/catalog'
import { useFlowStore } from '@/stores/flow'

/**
 * Step 3: pick up to three things that matter (the order of taps is the rank; no sliders),
 * then three yes/no questions. Every answer is optional.
 */
const flow = useFlowStore()
const catalog = useCatalogStore()
onMounted(() => catalog.loadCrops())

const icons: Record<Priority, Component> = {
  income_stability: CoinsIcon,
  simplicity: ClockIcon,
  soil_cover: LayersIcon,
  water_use: DropletIcon,
  forage_value: BeefIcon,
  nitrogen_fixing: BeanIcon,
  pest_break: BugOffIcon,
  market_suitability: StoreIcon,
}

const full = ref(false)

function tap(id: Priority) {
  const result = togglePriority(flow.answers.priorities, id)
  full.value = result.full
  if (!result.full) flow.setAnswers({ priorities: result.picked })
}

const rankOf = (id: Priority) => flow.answers.priorities.indexOf(id) + 1

// --- yes / no questions -------------------------------------------------------------
type YesNo = 'yes' | 'no' | ''

const livestock = computed<YesNo>({
  get: () => (flow.answers.livestock === null ? '' : flow.answers.livestock ? 'yes' : 'no'),
  set: (value) => flow.setAnswers({ livestock: value === '' ? null : value === 'yes' }),
})

// "Yes" opens the follow-up; the answer only counts once something is picked there
const contractOpen = ref<YesNo>(flow.answers.contracts.length ? 'yes' : '')
const excludeOpen = ref<YesNo>(flow.answers.excluded.length ? 'yes' : '')

function setContract(value: YesNo) {
  contractOpen.value = value
  if (value !== 'yes' && flow.answers.contracts.length) flow.setAnswers({ contracts: [] })
}
function setExclude(value: YesNo) {
  excludeOpen.value = value
  if (value !== 'yes' && flow.answers.excluded.length) flow.setAnswers({ excluded: [] })
}

function toggle(list: string[], id: string): string[] {
  return list.includes(id) ? list.filter((item) => item !== id) : [...list, id]
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <div class="flex flex-col gap-2">
      <h1
        id="panel-title"
        tabindex="-1"
        class="font-heading text-2xl leading-tight font-bold text-balance"
      >
        {{ copy.steps[2].title }}
      </h1>
      <p class="text-base">
        {{ copy.steps[2].hint }}
      </p>
    </div>

    <div class="grid grid-cols-2 gap-2">
      <button
        v-for="id in PRIORITIES"
        :key="id"
        type="button"
        class="tile"
        :aria-pressed="rankOf(id) > 0"
        @click="tap(id)"
      >
        <span
          v-if="rankOf(id)"
          class="absolute top-1.5 right-1.5 flex size-7 items-center justify-center rounded-full bg-foreground text-base font-bold text-background"
        >
          <span class="sr-only">{{ copy.priorities.rank(rankOf(id)) }}</span>
          <span aria-hidden="true">{{ rankOf(id) }}</span>
        </span>
        <component
          :is="icons[id]"
          class="size-7"
          aria-hidden="true"
        />
        <span>{{ copy.priorities.cards[id] }}</span>
      </button>
    </div>
    <p
      v-if="full"
      role="status"
      class="border-l-4 border-primary pl-3 text-base font-bold"
    >
      {{ copy.priorities.full }}
    </p>

    <section
      aria-labelledby="questions-title"
      class="flex flex-col gap-5"
    >
      <h2
        id="questions-title"
        class="font-heading text-xl font-bold"
      >
        {{ copy.priorities.questions }}
      </h2>

      <fieldset>
        <legend class="mb-2 text-base font-bold">
          {{ copy.priorities.livestock }}
        </legend>
        <ToggleGroup
          v-model="livestock"
          type="single"
          :spacing="2"
        >
          <ToggleGroupItem
            value="yes"
            class="chip"
          >
            {{ copy.yes }}
          </ToggleGroupItem>
          <ToggleGroupItem
            value="no"
            class="chip"
          >
            {{ copy.no }}
          </ToggleGroupItem>
        </ToggleGroup>
      </fieldset>

      <fieldset>
        <legend class="mb-2 text-base font-bold">
          {{ copy.priorities.contract }}
        </legend>
        <ToggleGroup
          :model-value="contractOpen"
          type="single"
          :spacing="2"
          @update:model-value="setContract(($event as YesNo) ?? '')"
        >
          <ToggleGroupItem
            value="yes"
            class="chip"
          >
            {{ copy.yes }}
          </ToggleGroupItem>
          <ToggleGroupItem
            value="no"
            class="chip"
          >
            {{ copy.no }}
          </ToggleGroupItem>
        </ToggleGroup>
        <div
          v-if="contractOpen === 'yes'"
          class="mt-3 flex flex-col gap-2"
        >
          <p class="text-base font-bold">
            {{ copy.priorities.contractWhich }}
          </p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="market in catalog.markets"
              :key="market"
              type="button"
              class="chip"
              :aria-pressed="flow.answers.contracts.includes(market)"
              @click="flow.setAnswers({ contracts: toggle(flow.answers.contracts, market) })"
            >
              {{ humanise(market) }}
            </button>
          </div>
        </div>
      </fieldset>

      <fieldset>
        <legend class="mb-2 text-base font-bold">
          {{ copy.priorities.exclude }}
        </legend>
        <ToggleGroup
          :model-value="excludeOpen"
          type="single"
          :spacing="2"
          @update:model-value="setExclude(($event as YesNo) ?? '')"
        >
          <ToggleGroupItem
            value="yes"
            class="chip"
          >
            {{ copy.yes }}
          </ToggleGroupItem>
          <ToggleGroupItem
            value="no"
            class="chip"
          >
            {{ copy.no }}
          </ToggleGroupItem>
        </ToggleGroup>
        <div
          v-if="excludeOpen === 'yes'"
          class="mt-3 flex flex-col gap-2"
        >
          <p class="text-base font-bold">
            {{ copy.priorities.excludeWhich }}
          </p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="crop in catalog.mainCrops"
              :key="crop.id"
              type="button"
              class="chip"
              :aria-pressed="flow.answers.excluded.includes(crop.id)"
              @click="flow.setAnswers({ excluded: toggle(flow.answers.excluded, crop.id) })"
            >
              {{ crop.name }}
            </button>
          </div>
        </div>
      </fieldset>
    </section>
  </div>
</template>
