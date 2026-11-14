<script setup lang="ts">
import { copy } from '@/copy/en'
</script>

<template>
  <!-- Shown under every recommendation: the farmer decides, with their advisor -->
  <p
    data-test="disclaimer"
    class="text-base font-bold"
  >
    {{ copy.disclaimer }}
  </p>
</template>
