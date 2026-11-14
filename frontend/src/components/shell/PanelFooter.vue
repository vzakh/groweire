<script setup lang="ts">
import { ArrowLeftIcon, ArrowRightIcon } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { copy } from '@/copy/en'
import { useFlowStore } from '@/stores/flow'

/**
 * Back and Next, always in view. On phones (`compact`) Back sits in the top bar, so this bar
 * holds one big primary button. Next is never greyed out: if something is missing, a line
 * above the buttons says what to do, so a tap always gets an answer.
 */
defineProps<{ compact?: boolean }>()

const flow = useFlowStore()
</script>

<template>
  <div
    v-if="flow.section || !compact || !flow.isLast"
    class="flex flex-col gap-2"
  >
    <p
      v-if="flow.blocked"
      role="alert"
      data-test="blocked"
      class="border-l-4 border-foreground pl-3 text-base font-bold"
    >
      {{ flow.blocked }}
    </p>
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
          class="disabled:opacity-70"
          :class="{ 'flex-1': flow.isLast }"
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
          data-test="next"
          :aria-busy="flow.busy"
          @click="flow.next()"
        >
          {{ copy.next }}
          <Spinner
            v-if="flow.busy"
            data-icon="inline-end"
          />
          <ArrowRightIcon
            v-else
            data-icon="inline-end"
          />
        </Button>
      </template>
    </div>
  </div>
</template>
