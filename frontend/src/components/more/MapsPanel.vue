<script setup lang="ts">
import { computed, onMounted } from 'vue'
import ErrorState from '@/components/common/ErrorState.vue'
import TermHelp from '@/components/common/TermHelp.vue'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { copy } from '@/copy/en'
import { monthName, monthShort } from '@/lib/format'
import { FIRST_MONTH, LAST_MONTH } from '@/lib/query'
import { RISK_LEVELS, STRESS_TYPES, type RiskLevel, type StressType } from '@/lib/risk'
import { useCatalogStore } from '@/stores/catalog'
import { useRiskStore } from '@/stores/risk'

/**
 * "More maps", for advisors and judges: every layer the API offers (NASA satellite pictures
 * and our risk map), the risk map for any month and weather type, and what the colours mean.
 */
const catalog = useCatalogStore()
const risk = useRiskStore()

onMounted(() => {
  catalog.loadLayers()
  // Open on the field's riskiest month rather than a month where the map is mostly "low"
  if (risk.selectedMonth) risk.explore.month = risk.selectedMonth
})

const layers = computed(() => catalog.layers?.layers ?? [])
const active = computed(() => catalog.layerById.get(risk.explore.layerId))
const isRisk = computed(() => risk.explore.layerId === 'stress_risk')

const months = Array.from({ length: LAST_MONTH - FIRST_MONTH + 1 }, (_, i) => FIRST_MONTH + i)
const types = Object.keys(STRESS_TYPES) as StressType[]
const levels = Object.keys(RISK_LEVELS) as RiskLevel[]

const month = computed({
  get: () => String(risk.explore.month),
  set: (value: string) => value && (risk.explore.month = Number(value)),
})
const type = computed({
  get: () => risk.explore.type ?? 'all',
  set: (value: string) => value && (risk.explore.type = value === 'all' ? null : (value as StressType)),
})

function pickLayer(id: string) {
  risk.explore.layerId = id
  risk.explore.date = ''
}

/** Glossary entries that explain a layer. */
const termFor: Record<string, string> = { ndvi: 'ndvi', soil_moisture: 'soil_moisture_anomaly' }
</script>

<template>
  <div class="flex flex-col gap-5">
    <h1
      id="panel-title"
      tabindex="-1"
      class="font-heading text-2xl leading-tight font-bold text-balance"
    >
      {{ copy.more.maps.label }}
    </h1>

    <ErrorState
      v-if="catalog.layersError"
      :error="catalog.layersError"
      @retry="catalog.loadLayers()"
    />
    <Skeleton
      v-else-if="!layers.length"
      class="h-40"
    />

    <template v-else>
      <fieldset class="flex flex-col gap-2">
        <legend class="mb-2 text-base font-bold">
          {{ copy.maps.layers }}
        </legend>
        <button
          v-for="layer in layers"
          :key="layer.id"
          type="button"
          class="chip chip-block"
          :aria-pressed="risk.explore.layerId === layer.id"
          @click="pickLayer(layer.id)"
        >
          <span class="font-bold">{{ layer.title }}</span>
          <span class="font-normal">{{ layer.description }}</span>
        </button>
      </fieldset>

      <template v-if="isRisk">
        <fieldset>
          <legend class="mb-2 text-base font-bold">
            {{ copy.maps.month }}
          </legend>
          <ToggleGroup
            v-model="month"
            type="single"
            class="grid w-full grid-cols-4 gap-2"
          >
            <ToggleGroupItem
              v-for="m in months"
              :key="m"
              :value="String(m)"
              class="chip"
              :aria-label="monthName(m)"
            >
              {{ monthShort(m) }}
            </ToggleGroupItem>
          </ToggleGroup>
        </fieldset>

        <fieldset>
          <legend class="mb-2 text-base font-bold">
            {{ copy.maps.type }}
          </legend>
          <ToggleGroup
            v-model="type"
            type="single"
            :spacing="2"
            class="w-full flex-wrap"
          >
            <ToggleGroupItem
              value="all"
              class="chip"
            >
              {{ copy.maps.allTypes }}
            </ToggleGroupItem>
            <ToggleGroupItem
              v-for="t in types"
              :key="t"
              :value="t"
              class="chip"
            >
              <component
                :is="STRESS_TYPES[t].icon"
                class="size-5"
                aria-hidden="true"
              />
              {{ STRESS_TYPES[t].word }}
            </ToggleGroupItem>
          </ToggleGroup>
        </fieldset>

        <p
          v-if="risk.explore.type === 'drought'"
          class="border-l-4 border-border pl-3 text-base"
        >
          {{ copy.maps.dryNote }}
        </p>

        <ErrorState
          v-if="risk.layerError"
          :error="risk.layerError"
          action=""
        />

        <!-- The cut-offs behind the three colours -->
        <ul class="flex flex-col gap-2">
          <li
            v-for="level in levels"
            :key="level"
            class="flex items-center gap-2 text-base"
          >
            <span
              class="flex w-24 shrink-0 items-center gap-1.5 rounded-lg px-2 py-1 font-bold ring-1 ring-foreground/30"
              :class="RISK_LEVELS[level].class"
            >
              <component
                :is="RISK_LEVELS[level].icon"
                class="size-5"
                aria-hidden="true"
              />
              {{ RISK_LEVELS[level].word }}
            </span>
            {{ copy.maps.legendCuts[level] }}
          </li>
        </ul>
        <p class="text-base">
          {{ copy.maps.cellHint }}
        </p>
      </template>

      <template v-else-if="active">
        <div class="flex flex-col gap-1">
          <label
            for="layer-day"
            class="text-base font-bold"
          >{{ copy.maps.day }}</label>
          <Input
            id="layer-day"
            type="date"
            :max="active.time.default"
            :model-value="risk.explore.date || active.time.default"
            class="h-12 w-52 text-base"
            @change="risk.explore.date = ($event.target as HTMLInputElement).value"
          />
        </div>
        <p class="text-base">
          {{ copy.maps.noPicture }}
        </p>
        <p class="text-base text-muted-foreground">
          {{ active.attribution }}
        </p>
        <TermHelp
          v-if="termFor[active.id]"
          :term="termFor[active.id]!"
        />
      </template>
    </template>
  </div>
</template>
