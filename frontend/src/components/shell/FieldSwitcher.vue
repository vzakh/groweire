<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import GrowEireLogo from '@/components/brand/GrowEireLogo.vue'
import { SidebarMenu, SidebarMenuButton, SidebarMenuItem } from '@/components/ui/sidebar'
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
      <SidebarMenuButton
        as-child
        size="lg"
        class="h-auto min-h-14 pt-3 hover:bg-white/10 hover:text-white active:bg-white/10 active:text-white"
      >
        <RouterLink
          to="/"
          :aria-label="copy.field.home"
        >
          <GrowEireLogo on-dark />
        </RouterLink>
      </SidebarMenuButton>
      <p class="truncate px-2 pb-1 text-sm text-white/85">
        {{ label }}
      </p>
    </SidebarMenuItem>
  </SidebarMenu>
</template>
