<script setup lang="ts">
import { computed, nextTick, watch } from 'vue'
import { InfoIcon } from '@lucide/vue'
import AnswerPanel from '@/components/answer/AnswerPanel.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import MapsPanel from '@/components/more/MapsPanel.vue'
import SourcesPanel from '@/components/more/SourcesPanel.vue'
import WordsPanel from '@/components/more/WordsPanel.vue'
import CropsPanel from '@/components/steps/CropsPanel.vue'
import PrioritiesPanel from '@/components/steps/PrioritiesPanel.vue'
import WherePanel from '@/components/steps/WherePanel.vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { copy } from '@/copy/en'
import { useFieldStore } from '@/stores/field'
import { useFlowStore } from '@/stores/flow'

/**
 * The one question (or the answer) for the current step, or one of the "More" pages.
 * The same panel sits in the sidebar on wide screens and under the map on phones.
 */
const flow = useFlowStore()
const field = useFieldStore()

const sections = { maps: MapsPanel, words: WordsPanel, sources: SourcesPanel }
const steps = [WherePanel, CropsPanel, PrioritiesPanel, AnswerPanel]

const panel = computed(() => (flow.section ? sections[flow.section] : steps[flow.step - 1]))

/** Steps 2 to 4 are about a field: wait for it, or say that the link is out of date. */
const needsField = computed(() => !flow.section && flow.step > 1)
const fieldReady = computed(() => field.field?.field_id === flow.fieldId)
const outsidePilot = computed(() => needsField.value && fieldReady.value && field.field?.pilot_coverage === false)

// Move focus to the new heading when the step changes, so screen readers announce it
watch(
  () => [flow.step, flow.section],
  async () => {
    await nextTick()
    // A new step starts at its top (on phones the router scrolls the page itself)
    document.querySelector('[data-slot=sidebar-content]')?.scrollTo({ top: 0 })
    document.getElementById('panel-title')?.focus({ preventScroll: true })
  },
)
</script>

<template>
  <section
    aria-labelledby="panel-title"
    class="flex flex-col gap-4 px-2 py-1"
  >
    <template v-if="needsField && !fieldReady">
      <ErrorState
        v-if="field.fieldError"
        :error="field.fieldError"
        :action="copy.field.findAgain"
        @retry="flow.startNew()"
      />
      <div
        v-else
        role="status"
        class="flex flex-col gap-3"
      >
        <h1
          id="panel-title"
          tabindex="-1"
          class="font-heading text-2xl font-bold"
        >
          {{ copy.field.loading }}
        </h1>
        <Skeleton class="h-32" />
      </div>
    </template>

    <template v-else>
      <Alert v-if="outsidePilot">
        <InfoIcon aria-hidden="true" />
        <AlertDescription class="text-base text-foreground">
          {{ copy.field.outsidePilot }}
        </AlertDescription>
      </Alert>
      <component :is="panel" />
    </template>
  </section>
</template>
