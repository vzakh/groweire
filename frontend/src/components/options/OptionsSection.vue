<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { PlusIcon, SproutIcon } from '@lucide/vue'
import ErrorState from '@/components/common/ErrorState.vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { copy } from '@/copy/en'
import { humanise } from '@/lib/format'
import { useCatalogStore } from '@/stores/catalog'
import { useRotationsStore } from '@/stores/rotations'
import OptionCard from './OptionCard.vue'

/**
 * The farmer's rotation next to the alternatives: the current one first, two alternatives
 * with it, and one more behind "Show another option" so the screen never shows a wall of cards.
 */
const rotations = useRotationsStore()
const catalog = useCatalogStore()

const VISIBLE = 3
const showAll = ref(false)

// Compare as soon as the answers are complete, and again whenever they change
watch(() => rotations.body, () => rotations.compare(), { immediate: true })
watch(() => rotations.result, () => {
  showAll.value = false
})

const strategies = computed(() => {
  const all = rotations.result?.strategies ?? []
  // The current rotation always comes first, whatever its score
  return [...all.filter((s) => s.is_current), ...all.filter((s) => !s.is_current)]
})
const shown = computed(() => (showAll.value ? strategies.value : strategies.value.slice(0, VISIBLE)))

const note = computed(() => rotations.result?.same_crop_note ?? null)
const noteSource = computed(() =>
  rotations.result?.provenance.find((item) => item.dataset_id === note.value?.source),
)
</script>

<template>
  <section
    aria-labelledby="options-title"
    class="flex flex-col gap-4"
  >
    <h2
      id="options-title"
      class="font-heading text-2xl leading-tight font-bold text-balance"
    >
      {{ copy.options.title }}
    </h2>

    <ErrorState
      v-if="rotations.error"
      :error="rotations.error"
      @retry="rotations.compare(true)"
    />
    <div
      v-else-if="!rotations.result"
      role="status"
      class="flex flex-col gap-3"
    >
      <p class="text-base">
        {{ copy.options.loading }}
      </p>
      <Skeleton class="h-40" />
      <Skeleton class="h-40" />
    </div>

    <template v-else>
      <Alert
        v-if="note"
        data-test="same-crop-note"
      >
        <SproutIcon aria-hidden="true" />
        <AlertDescription class="text-base text-foreground">
          <p>{{ note.text }}</p>
          <p v-if="note.source">
            <a
              v-if="noteSource"
              :href="noteSource.url"
              target="_blank"
              rel="noopener"
              class="underline underline-offset-4"
            >{{ copy.source }}: {{ noteSource.description }}</a>
            <template v-else>
              {{ copy.source }}: {{ humanise(note.source) }}
            </template>
          </p>
        </AlertDescription>
      </Alert>

      <OptionCard
        v-for="strategy in shown"
        :key="strategy.id"
        :strategy="strategy"
        :crops="catalog.cropById"
        :provenance="rotations.result.provenance"
        :weights="rotations.result.weights_used"
      />

      <Button
        v-if="!showAll && strategies.length > VISIBLE"
        variant="outline"
        size="tap"
        @click="showAll = true"
      >
        <PlusIcon data-icon="inline-start" />
        {{ copy.options.showAnother }}
      </Button>
    </template>
  </section>
</template>
