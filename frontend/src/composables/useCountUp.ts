import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

const calm = () =>
  document.documentElement.classList.contains('is-static') ||
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

/**
 * Counts from `from` to `to` once, when `target` scrolls into view (800 ms, ease-out).
 * Shows the final value immediately for reduced motion, ?static=1, or no IntersectionObserver.
 */
export function useCountUp(target: Ref<HTMLElement | null>, to: number, from = 0, duration = 800) {
  const value = ref(to)
  let io: IntersectionObserver | null = null
  let raf = 0

  onMounted(() => {
    if (calm() || !('IntersectionObserver' in window) || !target.value) return
    value.value = from
    io = new IntersectionObserver((entries) => {
      if (!entries.some((e) => e.isIntersecting)) return
      io?.disconnect()
      const start = performance.now()
      const tick = (now: number) => {
        const t = Math.min(1, (now - start) / duration)
        value.value = Math.round(from + (to - from) * (1 - Math.pow(1 - t, 3)))
        if (t < 1) raf = requestAnimationFrame(tick)
      }
      raf = requestAnimationFrame(tick)
    }, { threshold: 0.4 })
    io.observe(target.value)
  })
  onBeforeUnmount(() => {
    io?.disconnect()
    cancelAnimationFrame(raf)
  })
  return value
}
