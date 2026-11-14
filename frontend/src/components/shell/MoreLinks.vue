<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { BookOpenIcon, InfoIcon, MapIcon } from '@lucide/vue'
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { copy } from '@/copy/en'
import { useFlowStore, type Section } from '@/stores/flow'

/** Pages off the main path, for advisors and the curious: maps, words, sources. */
const flow = useFlowStore()

const links: { section: Section; icon: typeof MapIcon }[] = [
  { section: 'maps', icon: MapIcon },
  { section: 'words', icon: BookOpenIcon },
  { section: 'sources', icon: InfoIcon },
]
</script>

<template>
  <SidebarGroup>
    <SidebarGroupLabel>{{ copy.more.group }}</SidebarGroupLabel>
    <SidebarGroupContent>
      <SidebarMenu>
        <SidebarMenuItem
          v-for="link in links"
          :key="link.section"
        >
          <SidebarMenuButton
            as-child
            size="lg"
            :is-active="flow.section === link.section"
          >
            <RouterLink
              :to="flow.place({ section: link.section })"
              :aria-current="flow.section === link.section ? 'page' : undefined"
            >
              <component
                :is="link.icon"
                aria-hidden="true"
              />
              <span>{{ copy.more[link.section].label }}</span>
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarGroupContent>
  </SidebarGroup>
</template>
