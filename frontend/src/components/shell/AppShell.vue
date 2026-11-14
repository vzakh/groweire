<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Maximize2Icon, Minimize2Icon } from '@lucide/vue'
import MapCanvas from '@/components/map/MapCanvas.vue'
import MapLegend from '@/components/map/MapLegend.vue'
import { Button } from '@/components/ui/button'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { useLayout } from '@/composables/useLayout'
import { useMapScene } from '@/composables/useMapScene'
import { initTextScale } from '@/composables/useTextScale'
import { copy } from '@/copy/en'
import { riskCrop } from '@/lib/answers'
import { checkContract } from '@/lib/api'
import { useCatalogStore } from '@/stores/catalog'
import { useFieldStore } from '@/stores/field'
import { useFlowStore } from '@/stores/flow'
import { useRiskStore } from '@/stores/risk'
import AppSidebar from './AppSidebar.vue'
import FieldPanel from './FieldPanel.vue'
import PanelFooter from './PanelFooter.vue'
import TopBar from './TopBar.vue'

/**
 * The field app's frame. The map is the main canvas and is always on screen.
 * Wide screens: guided sidebar beside the map. Narrow screens: map on top, step panel below;
 * the steps are never hidden behind a menu button. Both use the same panel and the same map.
 */
const { isDesktop } = useLayout()
const flow = useFlowStore()
const field = useFieldStore()
const risk = useRiskStore()
const catalog = useCatalogStore()

// The saved text size applies here too, so the app does not depend on the landing page's start-up.
initTextScale()
useMapScene()

onMounted(() => {
  void checkContract()
})

// As soon as there is a field: load it (a shared link), then fetch in the background what the
// next steps need, so the answer is ready by the time the farmer gets there.
watch(
  () => flow.fieldId,
  async (id) => {
    if (!id) return
    await field.ensure(id)
    if (field.field?.field_id !== id) return
    field.loadConditions(id)
    risk.predict(id, null)
    catalog.loadCrops()
  },
  { immediate: true },
)
// Once last year's crop is known, ask for the risk weighed for that crop
watch(
  () => [flow.fieldId, riskCrop(flow.answers)] as const,
  ([id, crop]) => {
    if (id && crop) risk.predict(id, crop)
  },
  { immediate: true },
)

const onAnswer = computed(() => !flow.section && flow.step === 4)
// The answer has cards and a month strip, so it gets a wider sidebar
const sidebarWidth = computed(() => (onAnswer.value ? '32rem' : '26rem'))

// Phones: the map is tall while placing the field and short while answering questions
const bigMap = ref(false)
const mapHeight = computed(() => {
  if (bigMap.value) return 'h-[65svh]'
  if (flow.section === 'maps') return 'h-[50svh]'
  return !flow.section && flow.step === 1 ? 'h-[45svh]' : 'h-[30svh]'
})
</script>

<template>
  <SidebarProvider :style="{ '--sidebar-width': sidebarWidth }">
    <template v-if="isDesktop">
      <AppSidebar />
      <SidebarInset class="h-svh min-w-0 overflow-hidden">
        <TopBar />
        <div class="relative min-h-0 flex-1">
          <MapCanvas />
          <MapLegend />
        </div>
      </SidebarInset>
    </template>

    <div
      v-else
      class="flex min-h-svh w-full min-w-0 flex-col bg-background"
    >
      <TopBar compact />
      <div
        class="sticky top-0 z-10 shrink-0 border-b transition-[height]"
        :class="mapHeight"
      >
        <MapCanvas />
        <Button
          variant="outline"
          size="tap"
          class="absolute top-2 left-2 z-10 shadow-md"
          @click="bigMap = !bigMap"
        >
          <component
            :is="bigMap ? Minimize2Icon : Maximize2Icon"
            data-icon="inline-start"
          />
          {{ bigMap ? copy.map.smaller : copy.map.bigger }}
        </Button>
      </div>
      <!-- On a short phone map a floating legend would hide the map, so it sits under it -->
      <MapLegend inline />
      <main class="flex-1 px-2 py-5">
        <FieldPanel />
      </main>
      <PanelFooter
        compact
        class="sticky bottom-0 z-10 border-t bg-background px-4 py-3"
      />
    </div>
  </SidebarProvider>
</template>
