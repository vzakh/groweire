<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Skeleton } from '@/components/ui/skeleton'
import { useMap } from '@/composables/useMap'
import { copy } from '@/copy/en'

/**
 * The visible home of the app's single map. Mounting adopts the map element and unmounting
 * hands it back, so the map itself survives layout and step changes.
 */
const host = ref<HTMLElement>()
const { status, attach, detach } = useMap()

onMounted(() => attach(host.value!))
onBeforeUnmount(() => detach(host.value!))
</script>

<template>
  <div class="relative size-full bg-muted">
    <div
      ref="host"
      role="region"
      :aria-label="copy.map.label"
      class="absolute inset-0"
    />
    <div
      v-if="status !== 'ready'"
      class="absolute inset-0 flex items-center justify-center p-6"
    >
      <Skeleton
        v-if="status !== 'error'"
        class="absolute inset-0 rounded-none"
      />
      <p
        class="relative max-w-sm text-center text-base font-bold"
        role="status"
      >
        {{ status === 'error' ? copy.map.failed : copy.map.loading }}
      </p>
    </div>
  </div>
</template>
