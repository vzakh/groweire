<script setup lang="ts">
import { CheckIcon } from '@lucide/vue'
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { copy } from '@/copy/en'
import { STEP_COUNT, type Step } from '@/lib/query'
import { useFlowStore } from '@/stores/flow'

/**
 * The four steps as a progress list (done, now, next), not a menu.
 * A finished step can be tapped to go back to it; steps ahead are reached with Next.
 */
const flow = useFlowStore()

function stateOf(n: number): 'done' | 'now' | 'next' {
  if (n < flow.step) return 'done'
  return n === flow.step ? 'now' : 'next'
}
</script>

<template>
  <SidebarGroup>
    <SidebarGroupLabel>
      {{ copy.stepsGroup }} · {{ copy.stepCounter(flow.step, STEP_COUNT) }}
    </SidebarGroupLabel>
    <SidebarGroupContent>
      <SidebarMenu>
        <SidebarMenuItem
          v-for="(item, index) in copy.steps"
          :key="item.short"
        >
          <SidebarMenuButton
            size="lg"
            :is-active="stateOf(index + 1) === 'now'"
            :aria-current="stateOf(index + 1) === 'now' ? 'step' : undefined"
            :as="stateOf(index + 1) === 'next' ? 'div' : 'button'"
            :class="{ 'hover:bg-transparent active:bg-transparent': stateOf(index + 1) === 'next' }"
            @click="stateOf(index + 1) !== 'next' && flow.goTo((index + 1) as Step)"
          >
            <span
              class="flex size-8 shrink-0 items-center justify-center rounded-full border-2 font-bold"
              :class="{
                'border-primary bg-primary text-primary-foreground': stateOf(index + 1) === 'done',
                'border-sidebar-foreground bg-sidebar-foreground text-sidebar': stateOf(index + 1) === 'now',
                'border-sidebar-foreground': stateOf(index + 1) === 'next',
              }"
              aria-hidden="true"
            >
              <CheckIcon v-if="stateOf(index + 1) === 'done'" />
              <template v-else>{{ index + 1 }}</template>
            </span>
            <span>{{ item.short }}</span>
            <span class="sr-only">, {{ copy.stepState[stateOf(index + 1)] }}</span>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarGroupContent>
  </SidebarGroup>
</template>
