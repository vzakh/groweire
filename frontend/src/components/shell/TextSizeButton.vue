<script setup lang="ts">
import { Button } from '@/components/ui/button'
import { useTextScale } from '@/composables/useTextScale'

/** A+ : cycles the text size 100% → 125% → 150% → 100% and remembers it. */
const { cycle, label } = useTextScale()
</script>

<template>
  <Button
    variant="outline"
    size="icon-tap"
    class="text-lg font-bold"
    :aria-label="label"
    @click="cycle"
  >
    <span aria-hidden="true">A+</span>
  </Button>
</template>
