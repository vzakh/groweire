<script setup lang="ts">
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
  SidebarSeparator,
} from '@/components/ui/sidebar'
import { useFlowStore } from '@/stores/flow'
import FieldPanel from './FieldPanel.vue'
import FieldSwitcher from './FieldSwitcher.vue'
import MoreLinks from './MoreLinks.vue'
import PanelFooter from './PanelFooter.vue'
import StepProgress from './StepProgress.vue'

/**
 * The guided panel beside the map. It is a guide, not a navigation menu:
 * the current field on top, the four steps as a progress list, one question at a time,
 * and Back / Next always in view at the bottom.
 */
const flow = useFlowStore()
</script>

<template>
  <Sidebar collapsible="offcanvas">
    <!-- Dark green like the landing page bar, so the white logo and lime sprout stand out -->
    <SidebarHeader class="bg-forest-deep text-white">
      <FieldSwitcher />
    </SidebarHeader>

    <SidebarContent>
      <StepProgress v-if="!flow.section" />
      <SidebarGroup>
        <FieldPanel />
      </SidebarGroup>
      <SidebarSeparator />
      <MoreLinks />
    </SidebarContent>

    <SidebarFooter class="border-t p-3">
      <PanelFooter />
    </SidebarFooter>
  </Sidebar>
</template>
