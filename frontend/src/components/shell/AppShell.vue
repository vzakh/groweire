<script setup lang="ts">
import { onMounted } from 'vue'
import MapCanvas from '@/components/map/MapCanvas.vue'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { useLayout } from '@/composables/useLayout'
import { initTextScale } from '@/composables/useTextScale'
import { checkContract } from '@/lib/api'
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

// The saved text size applies here too, so the app does not depend on the landing page's start-up.
initTextScale()

onMounted(() => {
  void checkContract()
})
</script>

<template>
  <SidebarProvider :style="{ '--sidebar-width': '26rem' }">
    <template v-if="isDesktop">
      <AppSidebar />
      <SidebarInset class="h-svh min-w-0 overflow-hidden">
        <TopBar />
        <div class="relative min-h-0 flex-1">
          <MapCanvas />
        </div>
      </SidebarInset>
    </template>

    <div
      v-else
      class="flex min-h-svh w-full min-w-0 flex-col bg-background"
    >
      <TopBar compact />
      <div class="sticky top-0 z-10 h-[40svh] shrink-0 border-b">
        <MapCanvas />
      </div>
      <main class="flex-1 px-4 py-5">
        <FieldPanel />
      </main>
      <PanelFooter
        compact
        class="sticky bottom-0 z-10 border-t bg-background px-4 py-3"
      />
    </div>
  </SidebarProvider>
</template>
