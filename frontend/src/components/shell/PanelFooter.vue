<script setup lang="ts">
import { ArrowLeftIcon, ArrowRightIcon } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { copy } from '@/copy/en'
import { useFlowStore } from '@/stores/flow'

/**
 * Back and Next, always in view. On phones (`compact`) Back sits in the top bar,
 * so this bar holds one big primary button.
 */
defineProps<{ compact?: boolean }>()

const flow = useFlowStore()
</script>

<template>
  <div class="flex gap-2">
    <Button
      v-if="flow.section"
      variant="outline"
      size="tap"
      class="flex-1"
      @click="flow.backToField()"
    >
      <ArrowLeftIcon data-icon="inline-start" />
      {{ copy.backToField }}
    </Button>
    <template v-else>
      <Button
        v-if="!compact"
        variant="outline"
        size="tap"
        :disabled="flow.isFirst"
        @click="flow.back()"
      >
        <ArrowLeftIcon data-icon="inline-start" />
        {{ copy.back }}
      </Button>
      <Button
        v-if="!flow.isLast"
        size="tap"
        class="flex-1"
        @click="flow.next()"
      >
        {{ copy.next }}
        <ArrowRightIcon data-icon="inline-end" />
      </Button>
    </template>
  </div>
</template>
