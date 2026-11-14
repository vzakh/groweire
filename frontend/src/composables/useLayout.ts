import { computed } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { useTextScale } from './useTextScale'

/**
 * Sidebar beside the map on wide screens; map on top with the step panel below on narrow ones.
 * At the biggest text size the sidebar needs more room, so the stacked layout holds until 1280px.
 */
export function useLayout() {
  const wide = useMediaQuery('(min-width: 1024px)')
  const veryWide = useMediaQuery('(min-width: 1280px)')
  const { scale } = useTextScale()

  const isDesktop = computed(() => (scale.value === 150 ? veryWide.value : wide.value))

  return { isDesktop }
}
