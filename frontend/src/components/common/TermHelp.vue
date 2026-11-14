<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { CircleHelpIcon } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverDescription, PopoverTitle, PopoverTrigger } from '@/components/ui/popover'
import { copy } from '@/copy/en'
import { useCatalogStore } from '@/stores/catalog'

/**
 * "What does this mean?" for one technical word. The plain meaning comes from the API's
 * glossary; technical terms only ever appear behind this button.
 */
const props = defineProps<{ term: string }>()

const catalog = useCatalogStore()
onMounted(() => catalog.loadGlossary())

const entry = computed(() => catalog.termById.get(props.term))
</script>

<template>
  <Popover v-if="entry">
    <PopoverTrigger as-child>
      <Button
        variant="outline"
        size="tap"
        class="self-start"
      >
        <CircleHelpIcon data-icon="inline-start" />
        {{ copy.whatDoesThisMean }}
      </Button>
    </PopoverTrigger>
    <PopoverContent
      align="start"
      class="w-80 max-w-[calc(100vw-2rem)] gap-2 p-4"
    >
      <PopoverTitle class="text-base font-bold">
        {{ entry.title }}
      </PopoverTitle>
      <PopoverDescription class="text-base text-foreground">
        {{ entry.text }}
      </PopoverDescription>
    </PopoverContent>
  </Popover>
</template>
