<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import GrowEireLogo from '@/components/brand/GrowEireLogo.vue'
</script>

<template>
  <!-- Workspace shell only; the field workspace modules come next. -->
  <div class="flex min-h-svh flex-col bg-mist">
    <header class="flex min-h-(--toolbar-h) items-center gap-4 border-b border-hairline bg-white px-4 sm:px-6">
      <RouterLink
        to="/"
        class="inline-flex min-h-12 items-center gap-2 rounded-full px-3 text-[1rem] font-bold text-forest hover:bg-mist"
      >
        <ArrowLeft
          class="size-5"
          aria-hidden="true"
        />
        Back to GrowÉire Home
      </RouterLink>
      <span class="ml-auto"><GrowEireLogo /></span>
    </header>
    <main class="flex flex-1 items-center justify-center p-6">
      <p class="max-w-md text-center text-[1.125rem] text-muted-ink">
        The field workspace opens here.
      </p>
    </main>
  </div>
</template>
