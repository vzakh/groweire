<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import {
  ArrowLeftIcon,
  BookOpenIcon,
  ChevronDownIcon,
  CircleHelpIcon,
  EllipsisIcon,
  InfoIcon,
  MapIcon,
  PanelLeftIcon,
  RotateCcwIcon,
} from '@lucide/vue'
import GrowEireLogo from '@/components/brand/GrowEireLogo.vue'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
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
import { STEP_COUNT, type Step } from '@/lib/query'
import { useFlowStore, type Section } from '@/stores/flow'
import TextSizeButton from './TextSizeButton.vue'
import { useStartAgain } from '@/composables/useStartAgain'

/**
 * Bar above the map. Wide screens: show/hide the steps, where you are, text size, word help.
 * Phones (`compact`): brand, text size, word help and the off-path "More" pages, then a row
 * with the step counter and Back, so both are always in view.
 */
defineProps<{ compact?: boolean }>()

const flow = useFlowStore()
const { state, toggleSidebar } = useSidebar()
const startAgain = useStartAgain()

/** Buttons on the dark green phone bar: outlined in white, like the sidebar header on desktop. */
const ON_DARK =
  'border-white/40 bg-transparent text-white shadow-none hover:bg-white/10 hover:text-white dark:bg-transparent dark:hover:bg-white/10'

/** The step just before the current one (from step 3 on; on step 2 it is "Your field" = step 1). */
const earlier = computed(() =>
  flow.step > 2 ? [{ label: copy.steps[flow.step - 2]!.short, step: (flow.step - 1) as Step }] : [],
)
const SECTIONS: Section[] = ['maps', 'words', 'sources']
/** "Your field" gives way first: below 44rem whenever it is a link, below 58rem when a step-back link follows */
const lead = computed(() => ({
  '@max-[44rem]:hidden': Boolean(flow.section) || flow.step > 1,
  '@max-[58rem]:hidden': earlier.value.length > 0,
}))
const LINK = 'cursor-pointer whitespace-nowrap rounded-sm underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-ring'

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
      <!--
        Every part but the last is a link. Steps: "Your field" goes to step 1, then the step just
        before this one (one step back). More pages: "Your field" goes back to the step you were
        on, "More" opens the list of More pages. A tight bar drops "Your field" when it can.
      -->
      <BreadcrumbList class="flex-nowrap text-base text-foreground">
        <BreadcrumbItem :class="lead">
          <BreadcrumbLink
            v-if="flow.section || flow.step > 1"
            as="button"
            type="button"
            :class="LINK"
            @click="flow.section ? flow.backToField() : flow.goTo(1)"
          >
            {{ copy.stepsGroup }}
          </BreadcrumbLink>
          <template v-else>
            {{ copy.stepsGroup }}
          </template>
        </BreadcrumbItem>
        <BreadcrumbSeparator :class="lead" />

        <template v-if="flow.section">
          <BreadcrumbItem>
            <DropdownMenu>
              <DropdownMenuTrigger
                :class="[LINK, 'inline-flex items-center gap-1']"
              >
                {{ copy.more.group }}
                <ChevronDownIcon
                  class="size-4"
                  aria-hidden="true"
                />
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="start"
                class="min-w-56"
              >
                <DropdownMenuItem
                  v-for="id in SECTIONS"
                  :key="id"
                  class="min-h-11"
                  @select="flow.openSection(id)"
                >
                  {{ copy.more[id].label }}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
        </template>

        <template
          v-for="item in flow.section ? [] : earlier"
          :key="item.step"
        >
          <!-- One step back -->
          <BreadcrumbItem>
            <BreadcrumbLink
              as="button"
              type="button"
              :class="LINK"
              @click="flow.goTo(item.step)"
            >
              {{ item.label }}
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
        </template>

        <BreadcrumbItem class="min-w-0">
          <BreadcrumbPage class="truncate font-bold whitespace-nowrap">
            {{ here }}
          </BreadcrumbPage>
        </BreadcrumbItem>
      </BreadcrumbList>
    </Breadcrumb>

    <div class="ml-auto flex items-center gap-2">
      <Button
        variant="outline"
        size="tap"
        :aria-label="copy.startAgainLabel"
        @click="startAgain"
      >
        <RotateCcwIcon data-icon="inline-start" />
        <!-- Label only when the bar is wide; the trail needs the room first -->
        <span class="@max-[62rem]:hidden">{{ copy.startAgain }}</span>
      </Button>
      <TextSizeButton />
      <Button
        as-child
        variant="outline"
        size="tap"
      >
        <RouterLink :to="flow.place({ section: 'words' })">
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
    <!-- Dark green like the desktop sidebar header; the logo has the same hover -->
    <div class="flex h-(--app-header-h) items-center gap-2 bg-forest-deep px-2 text-white">
      <RouterLink
        to="/"
        class="tap inline-flex items-center rounded-md px-2 pt-3 pb-1 outline-hidden hover:bg-white/10 focus-visible:ring-2 focus-visible:ring-white"
        :aria-label="copy.field.home"
      >
        <GrowEireLogo on-dark />
      </RouterLink>
      <div class="ml-auto flex items-center gap-2 pr-2">
        <TextSizeButton :class="ON_DARK" />
        <!-- At the biggest text size a phone has no room for this button; the same page is in "More" -->
        <Button
          as-child
          variant="outline"
          size="tap"
          :class="['@max-[20rem]:hidden', ON_DARK]"
        >
          <RouterLink :to="flow.place({ section: 'words' })">
            <CircleHelpIcon data-icon="inline-start" />
            {{ copy.words }}
          </RouterLink>
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button
              variant="outline"
              size="icon-tap"
              :class="ON_DARK"
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
                class="min-h-12"
                @select="startAgain"
              >
                <RotateCcwIcon aria-hidden="true" />
                {{ copy.startAgain }}
              </DropdownMenuItem>
              <DropdownMenuItem
                as-child
                class="min-h-12"
              >
                <RouterLink :to="flow.place({ section: 'maps' })">
                  <MapIcon aria-hidden="true" />
                  {{ copy.more.maps.label }}
                </RouterLink>
              </DropdownMenuItem>
              <DropdownMenuItem
                as-child
                class="min-h-12"
              >
                <RouterLink :to="flow.place({ section: 'words' })">
                  <BookOpenIcon aria-hidden="true" />
                  {{ copy.more.words.label }}
                </RouterLink>
              </DropdownMenuItem>
              <DropdownMenuItem
                as-child
                class="min-h-12"
              >
                <RouterLink :to="flow.place({ section: 'sources' })">
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
        class="disabled:opacity-70"
        :disabled="flow.isFirst"
        @click="flow.back()"
      >
        <ArrowLeftIcon data-icon="inline-start" />
        {{ copy.back }}
      </Button>
    </div>
  </header>
</template>
