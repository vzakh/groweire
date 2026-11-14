<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ChevronsUpDownIcon, HouseIcon, PencilIcon, PlusIcon } from '@lucide/vue'
import GrowEireLogo from '@/components/brand/GrowEireLogo.vue'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { SidebarMenu, SidebarMenuButton, SidebarMenuItem } from '@/components/ui/sidebar'
import { copy } from '@/copy/en'
import { hectares } from '@/lib/format'
import { useFieldStore } from '@/stores/field'
import { useFlowStore } from '@/stores/flow'

/** Sidebar header: the brand and the current field, with the two ways to start over. */
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
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <SidebarMenuButton
            size="lg"
            class="h-auto min-h-14"
            :aria-label="`${copy.brand}. ${label}. ${copy.field.menuLabel}`"
          >
            <span class="flex min-w-0 flex-1 flex-col text-left">
              <GrowEireLogo />
              <span class="truncate">{{ label }}</span>
            </span>
            <ChevronsUpDownIcon aria-hidden="true" />
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="start"
          class="w-(--reka-dropdown-menu-trigger-width) min-w-64"
        >
          <DropdownMenuGroup>
            <DropdownMenuItem
              class="min-h-12"
              @select="flow.startNew()"
            >
              <PlusIcon aria-hidden="true" />
              {{ copy.field.startNew }}
            </DropdownMenuItem>
            <DropdownMenuItem
              v-if="flow.fieldId"
              class="min-h-12"
              @select="flow.goTo(2)"
            >
              <PencilIcon aria-hidden="true" />
              {{ copy.field.changeAnswers }}
            </DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem
              as-child
              class="min-h-12"
            >
              <RouterLink to="/">
                <HouseIcon aria-hidden="true" />
                {{ copy.field.home }}
              </RouterLink>
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarMenuItem>
  </SidebarMenu>
</template>
