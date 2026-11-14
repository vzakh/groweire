<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { copy } from '@/copy/en'
import { useFlowStore } from '@/stores/flow'

/**
 * The one question (or answer) for the current step. The same panel sits in the sidebar on
 * wide screens and under the map on phones. The step content itself arrives with each step's
 * task; until then the panel names the step and says so.
 */
const flow = useFlowStore()

const content = computed(() => {
  if (flow.section) {
    const page = copy.more[flow.section]
    return { title: page.label, hint: page.hint }
  }
  return copy.steps[flow.step - 1]!
})

// Move focus to the new heading when the step changes, so screen readers announce it
const heading = ref<HTMLElement>()
watch(
  () => [flow.step, flow.section],
  async () => {
    await nextTick()
    heading.value?.focus()
  },
)
</script>

<template>
  <section
    aria-labelledby="panel-title"
    class="flex flex-col gap-3 px-2 py-1"
  >
    <h1
      id="panel-title"
      ref="heading"
      tabindex="-1"
      class="font-heading text-2xl leading-tight font-bold text-balance"
    >
      {{ content.title }}
    </h1>
    <p class="text-base">
      {{ content.hint }}
    </p>
    <p class="border-l-4 border-border pl-3 text-base">
      {{ copy.notBuiltYet }}
    </p>
  </section>
</template>
