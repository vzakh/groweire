<script setup lang="ts">
import { copy } from '@/copy/en'
import { serverWaking } from '@/lib/api'

/** Shown while an API request is slow: the free-hosting API is waking up (see lib/api.ts). */
</script>

<template>
  <div
    class="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex justify-center px-4 pb-[max(1rem,env(safe-area-inset-bottom))]"
    role="status"
    aria-live="polite"
  >
    <div
      v-if="serverWaking"
      class="pointer-events-auto flex max-w-md items-start gap-3 rounded-xl bg-forest-deep px-4 py-3 text-white shadow-lg"
    >
      <span
        class="mt-1 size-4 shrink-0 animate-spin rounded-full border-2 border-white/30 border-t-lime motion-reduce:animate-none"
        aria-hidden="true"
      />
      <p class="text-[0.9375rem] leading-snug">
        <strong class="block">{{ copy.waking.title }}</strong>
        {{ copy.waking.text }}
      </p>
    </div>
  </div>
</template>
