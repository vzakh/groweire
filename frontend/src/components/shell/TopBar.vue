<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import {
  ArrowLeftIcon,
  BookOpenIcon,
  CircleHelpIcon,
  EllipsisIcon,
  InfoIcon,
  MapIcon,
  PanelLeftIcon,
} from '@lucide/vue'
import GrowEireLogo from '@/components/brand/GrowEireLogo.vue'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useSidebar } from '@/components/ui/sidebar'
import { copy } from '@/copy/en'
import { STEP_COUNT } from '@/lib/query'
import { useFlowStore } from '@/stores/flow'
import TextSizeButton from './TextSizeButton.vue'

/**
 * Bar above the map. Wide screens: show/hide the steps, where you are, text size, word help.
 * Phones (`compact`): brand, text size, word help and the off-path "More" pages, then a row
 * with the step counter and Back, so both are always in view.
 */
defineProps<{ compact?: boolean }>()

const flow = useFlowStore()
const { state, toggleSidebar } = useSidebar()

const here = computed(() =>
  flow.section ? copy.more[flow.section].label : copy.steps[flow.step - 1]!.short,
)
</script>

<template>
  <header
    v-if="!compact"
    class="@container flex h-(--app-header-h) shrink-0 items-center gap-3 border-b bg-background px-3"
  >
    <Button
      variant="outline"
      :size="state === 'collapsed' ? 'tap' : 'icon-tap'"
      :aria-label="state === 'collapsed' ? undefined : copy.panel.hide"
      @click="toggleSidebar"
    >
      <PanelLeftIcon :data-icon="state === 'collapsed' ? 'inline-start' : undefined" />
      <template v-if="state === 'collapsed'">
        {{ copy.panel.show }}
      </template>
    </Button>

    <Breadcrumb class="min-w-0">
      <!-- When the bar is tight (big text, narrow window) only the current place is shown -->
      <BreadcrumbList class="flex-nowrap text-base text-foreground">
        <BreadcrumbItem class="@max-[44rem]:hidden">
          {{ flow.section ? copy.more.group : copy.stepsGroup }}
        </BreadcrumbItem>
        <BreadcrumbSeparator class="@max-[44rem]:hidden" />
        <BreadcrumbItem class="min-w-0">
          <BreadcrumbPage class="truncate font-bold">
            {{ here }}
          </BreadcrumbPage>
        </BreadcrumbItem>
      </BreadcrumbList>
    </Breadcrumb>

    <div class="ml-auto flex items-center gap-2">
      <TextSizeButton />
      <Button
        as-child
        variant="outline"
        size="tap"
      >
        <RouterLink to="/app/words">
          <CircleHelpIcon data-icon="inline-start" />
          <span class="@max-[44rem]:hidden">{{ copy.whatDoesThisMean }}</span>
          <span class="@min-[44rem]:hidden">{{ copy.words }}</span>
        </RouterLink>
      </Button>
    </div>
  </header>

  <header
    v-else
    class="@container shrink-0 border-b bg-background"
  >
    <div class="flex h-(--app-header-h) items-center gap-2 px-4">
      <RouterLink
        to="/"
        class="tap inline-flex items-center"
        :aria-label="copy.field.home"
      >
        <GrowEireLogo />
      </RouterLink>
      <div class="ml-auto flex items-center gap-2">
        <TextSizeButton />
        <!-- At the biggest text size a phone has no room for this button; the same page is in "More" -->
        <Button
          as-child
          variant="outline"
          size="tap"
          class="@max-[20rem]:hidden"
        >
          <RouterLink to="/app/words">
            <CircleHelpIcon data-icon="inline-start" />
            {{ copy.words }}
          </RouterLink>
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button
              variant="outline"
              size="icon-tap"
              :aria-label="copy.more.menu"
            >
              <EllipsisIcon />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            class="min-w-64"
          >
            <DropdownMenuGroup>
              <DropdownMenuItem
                as-child
                class="min-h-12"
              >
                <RouterLink to="/app/maps">
                  <MapIcon aria-hidden="true" />
                  {{ copy.more.maps.label }}
                </RouterLink>
              </DropdownMenuItem>
              <DropdownMenuItem
                as-child
                class="min-h-12"
              >
                <RouterLink to="/app/words">
                  <BookOpenIcon aria-hidden="true" />
                  {{ copy.more.words.label }}
                </RouterLink>
              </DropdownMenuItem>
              <DropdownMenuItem
                as-child
                class="min-h-12"
              >
                <RouterLink to="/app/sources">
                  <InfoIcon aria-hidden="true" />
                  {{ copy.more.sources.label }}
                </RouterLink>
              </DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>

    <div class="flex min-h-14 items-center justify-between gap-3 px-4 pb-2">
      <p class="font-bold">
        {{ flow.section ? here : copy.stepCounter(flow.step, STEP_COUNT) }}
      </p>
      <Button
        v-if="flow.section"
        variant="outline"
        size="tap"
        @click="flow.backToField()"
      >
        <ArrowLeftIcon data-icon="inline-start" />
        {{ copy.backToField }}
      </Button>
      <Button
        v-else
        variant="outline"
        size="tap"
        :disabled="flow.isFirst"
        @click="flow.back()"
      >
        <ArrowLeftIcon data-icon="inline-start" />
        {{ copy.back }}
      </Button>
    </div>
  </header>
</template>
