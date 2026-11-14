<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { MapPinIcon, PencilLineIcon, SatelliteIcon, SearchIcon, Undo2Icon, XIcon } from '@lucide/vue'
import ErrorState from '@/components/common/ErrorState.vue'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { copy } from '@/copy/en'
import { acres, hectares } from '@/lib/format'
import { useCatalogStore } from '@/stores/catalog'
import { MAX_AREA_HA, MIN_AREA_HA, useFieldStore } from '@/stores/field'
import { useFlowStore } from '@/stores/flow'

/**
 * Step 1: find the place, tap the field, say roughly how big it is. Drawing the edges is
 * there for those who want it, never required. "Next" creates the field.
 */
const flow = useFlowStore()
const field = useFieldStore()
const catalog = useCatalogStore()

const SIZES = [2, 5, 10, 20, 40]
const query = ref(field.searched)
const otherSize = ref(!SIZES.includes(field.areaHa))

const sizeChoice = computed({
  get: () => (otherSize.value ? 'other' : String(field.areaHa)),
  set: (value: string) => {
    if (!value) return
    otherSize.value = value === 'other'
    if (value !== 'other') field.setArea(Number(value))
  },
})

/** The field already made, shown while no new spot has been tapped. */
const existing = computed(() =>
  flow.fieldId && field.field?.field_id === flow.fieldId && !field.hasPlacement && !field.drawing
    ? field.field
    : null,
)

const satelliteNote = computed(() => catalog.layerById.get('true_colour')?.description)

function onOtherSize(event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  if (Number.isFinite(value) && value > 0) field.setArea(value)
}

async function beforeNext() {
  if (field.drawing && !field.hasDrawing) return copy.where.needCorners
  if (!field.hasPlacement) return existing.value ? true : copy.where.needPlacement
  const created = await field.create()
  // On failure the error shows below and the person stays here
  if (created) await flow.goTo(2, created.field_id)
  return false
}

// The "tap the map first" line has done its job once something is marked
watch(
  () => [field.hasPlacement, field.corners.length],
  () => {
    flow.blocked = null
  },
)

onMounted(() => {
  catalog.loadLayers()
  flow.setGuard(beforeNext)
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
      {{ copy.steps[0].title }}
    </h1>

    <Alert v-if="existing">
      <MapPinIcon aria-hidden="true" />
      <AlertTitle class="text-base font-bold">
        {{ copy.where.current }} {{ copy.field.summary(existing.name, hectares(existing.area_ha)) }}
      </AlertTitle>
      <AlertDescription class="text-base text-foreground">
        {{ copy.where.currentHint }}
      </AlertDescription>
    </Alert>

    <!-- Search runs only on submit: one request per search, never while typing -->
    <form
      role="search"
      class="flex flex-col gap-2"
      @submit.prevent="field.search(query)"
    >
      <label
        for="place-search"
        class="text-base font-bold"
      >{{ copy.where.searchLabel }}</label>
      <div class="flex gap-2">
        <Input
          id="place-search"
          v-model="query"
          type="search"
          autocomplete="off"
          enterkeyhint="search"
          :placeholder="copy.where.searchPlaceholder"
          class="h-12 min-w-0 flex-1 text-base"
        />
        <Button
          type="submit"
          size="tap"
          :disabled="field.placesLoading"
        >
          <Spinner
            v-if="field.placesLoading"
            data-icon="inline-start"
          />
          <SearchIcon
            v-else
            data-icon="inline-start"
          />
          {{ copy.where.searchButton }}
        </Button>
      </div>
    </form>

    <p
      v-if="field.placesLoading"
      role="status"
      class="text-base"
    >
      {{ copy.where.searching }}
    </p>
    <ErrorState
      v-else-if="field.placesError"
      :error="field.placesError"
      action=""
    />
    <section
      v-else-if="field.places"
      aria-labelledby="results-title"
      class="flex flex-col gap-2"
    >
      <template v-if="field.places.results.length">
        <h2
          id="results-title"
          class="text-base font-bold"
        >
          {{ copy.where.results }}
        </h2>
        <ul class="flex flex-col gap-2">
          <li
            v-for="result in field.places.results"
            :key="`${result.name}|${result.lon}|${result.lat}`"
          >
            <Button
              variant="outline"
              size="tap"
              class="h-auto min-h-12 w-full justify-start py-2 text-left whitespace-normal"
              :aria-pressed="field.place === result"
              @click="field.choosePlace(result)"
            >
              <MapPinIcon data-icon="inline-start" />
              {{ result.name }}
            </Button>
          </li>
        </ul>
        <p class="text-base text-muted-foreground">
          {{ field.places.attribution }}
        </p>
      </template>
      <p
        v-else
        class="text-base"
      >
        {{ copy.where.noResults }}
      </p>
    </section>

    <!-- Placing by tap (the default) -->
    <template v-if="!field.drawing">
      <p class="border-l-4 border-primary pl-3 text-base font-bold">
        {{ field.point ? copy.where.placed : copy.where.tapHint }}
      </p>

      <fieldset
        v-if="field.point"
        class="flex flex-col gap-2"
      >
        <legend class="mb-2 text-base font-bold">
          {{ copy.where.sizeQuestion }}
        </legend>
        <ToggleGroup
          v-model="sizeChoice"
          type="single"
          :spacing="2"
          class="w-full flex-wrap"
        >
          <ToggleGroupItem
            v-for="size in SIZES"
            :key="size"
            :value="String(size)"
            class="chip"
          >
            {{ copy.where.size(size, acres(size)) }}
          </ToggleGroupItem>
          <ToggleGroupItem
            value="other"
            class="chip"
          >
            {{ copy.where.sizeOther }}
          </ToggleGroupItem>
        </ToggleGroup>
        <div
          v-if="otherSize"
          class="flex flex-col gap-1"
        >
          <label
            for="other-size"
            class="text-base font-bold"
          >{{ copy.where.sizeOtherLabel }}</label>
          <Input
            id="other-size"
            type="number"
            inputmode="decimal"
            :min="MIN_AREA_HA"
            :max="MAX_AREA_HA"
            step="0.1"
            :model-value="field.areaHa"
            class="h-12 w-40 text-base"
            aria-describedby="other-size-hint"
            @change="onOtherSize"
          />
          <p
            id="other-size-hint"
            class="text-base text-muted-foreground"
          >
            {{ copy.where.sizeRange }}
          </p>
        </div>
      </fieldset>

      <div
        v-if="field.place && !field.point"
        class="flex flex-col gap-1"
      >
        <Button
          variant="outline"
          size="tap"
          class="self-start"
          @click="field.usePlace()"
        >
          <MapPinIcon data-icon="inline-start" />
          {{ copy.where.usePlace }}
        </Button>
        <p class="text-base text-muted-foreground">
          {{ copy.where.usePlaceHint }}
        </p>
      </div>
    </template>

    <!-- Drawing the edges (optional) -->
    <section
      v-else
      class="flex flex-col gap-3"
    >
      <p class="border-l-4 border-primary pl-3 text-base font-bold">
        {{ copy.where.drawHint }}
      </p>
      <p
        role="status"
        class="text-base"
      >
        {{ copy.where.drawCorners(field.corners.length) }}
        <template v-if="field.hasDrawing">
          · {{ copy.where.drawArea(hectares(field.drawnAreaHa)) }}
        </template>
      </p>
      <div class="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="tap"
          :disabled="!field.corners.length"
          @click="field.undoCorner()"
        >
          <Undo2Icon data-icon="inline-start" />
          {{ copy.where.drawUndo }}
        </Button>
        <Button
          variant="outline"
          size="tap"
          @click="field.stopDrawing()"
        >
          <XIcon data-icon="inline-start" />
          {{ copy.where.drawStop }}
        </Button>
      </div>
    </section>

    <div class="flex flex-col gap-2">
      <Button
        variant="outline"
        size="tap"
        class="self-start"
        :aria-pressed="field.satellite"
        @click="field.satellite = !field.satellite"
      >
        <SatelliteIcon data-icon="inline-start" />
        {{ field.satellite ? copy.where.satelliteHide : copy.where.satelliteShow }}
      </Button>
      <p
        v-if="field.satellite && satelliteNote"
        class="text-base text-muted-foreground"
      >
        {{ satelliteNote }}
      </p>
      <Button
        v-if="!field.drawing"
        variant="outline"
        size="tap"
        class="self-start"
        @click="field.startDrawing()"
      >
        <PencilLineIcon data-icon="inline-start" />
        {{ copy.where.draw }}
      </Button>
    </div>

    <ErrorState
      v-if="field.fieldError && !field.field"
      :error="field.fieldError"
      action=""
    />
  </div>
</template>
