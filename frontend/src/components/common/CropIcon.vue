<script setup lang="ts">
import { computed } from 'vue'
import { BeanIcon, CarrotIcon, CloverIcon, Flower2Icon, LeafIcon, SproutIcon, WheatIcon } from '@lucide/vue'

/**
 * A simple picture for a crop, chosen by its plant family. The crop's name is always shown
 * next to it; the picture only helps people find a crop at a glance.
 */
const props = defineProps<{ family?: string }>()

const icons: Record<string, typeof WheatIcon> = {
  cereal: WheatIcon,
  legume: BeanIcon,
  brassica: Flower2Icon,
  solanaceae: CarrotIcon,
  maize: SproutIcon,
  ley: CloverIcon,
}

const icon = computed(() => icons[props.family ?? ''] ?? LeafIcon)
</script>

<template>
  <component
    :is="icon"
    aria-hidden="true"
  />
</template>
