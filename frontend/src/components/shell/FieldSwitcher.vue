<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import GrowEireLogo from '@/components/brand/GrowEireLogo.vue'
import { SidebarMenu, SidebarMenuItem } from '@/components/ui/sidebar'
import { copy } from '@/copy/en'
import { hectares } from '@/lib/format'
import { useFieldStore } from '@/stores/field'
import { useFlowStore } from '@/stores/flow'

/** Sidebar header: the logo, which goes back to the landing page, and the current field. */
const flow = useFlowStore()
const field = useFieldStore()

const label = computed(() => {
  const current = field.field
  return current && current.field_id === flow.fieldId
    ? copy.field.summary(current.name, hectares(current.area_ha))
    : copy.field.none
})
</script>

<template>
  <SidebarMenu>
    <SidebarMenuItem>
      <!--
        A plain link, not SidebarMenuButton: that one truncates its last child (overflow hidden),
        which cut off the sprout over the E.
      -->
      <RouterLink
        to="/"
        class="flex min-h-14 items-center rounded-md px-2 pt-3 pb-1 outline-hidden hover:bg-white/10 focus-visible:ring-2 focus-visible:ring-sidebar-ring"
        :aria-label="copy.field.home"
      >
        <GrowEireLogo on-dark />
      </RouterLink>
      <p class="truncate px-2 pb-1 text-sm text-white/85">
        {{ label }}
      </p>
    </SidebarMenuItem>
  </SidebarMenu>
</template>
