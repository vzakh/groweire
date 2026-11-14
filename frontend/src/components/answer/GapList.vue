<script setup lang="ts">
import { computed, ref } from 'vue'
import { InfoIcon } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { copy } from '@/copy/en'
import type { Schemas } from '@/lib/api'

/**
 * What we do not know, always on screen and never hidden: the first two lines show,
 * the rest are one tap away. The sentences are the API's own.
 */
const props = defineProps<{ gaps: Schemas['InformationGap'][] }>()

const VISIBLE = 2
const all = ref(false)
const shown = computed(() => (all.value ? props.gaps : props.gaps.slice(0, VISIBLE)))
const hidden = computed(() => props.gaps.length - VISIBLE)
</script>

<template>
  <section
    v-if="gaps.length"
    aria-labelledby="gaps-title"
    class="flex flex-col gap-2 rounded-xl bg-muted p-4"
  >
    <h2
      id="gaps-title"
      class="flex items-center gap-2 text-base font-bold"
    >
      <InfoIcon
        class="size-5"
        aria-hidden="true"
      />
      {{ copy.answer.gaps }}
    </h2>
    <ul class="flex list-disc flex-col gap-1 pl-5 text-base">
      <li
        v-for="gap in shown"
        :key="gap.code"
        data-test="gap"
      >
        {{ gap.text }}
      </li>
    </ul>
    <Button
      v-if="hidden > 0"
      variant="outline"
      size="tap"
      class="self-start"
      :aria-expanded="all"
      @click="all = !all"
    >
      {{ all ? copy.answer.gapsLess : copy.answer.gapsMore(hidden) }}
    </Button>
  </section>
</template>
