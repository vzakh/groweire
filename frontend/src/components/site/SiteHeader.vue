<script setup lang="ts">
/**
 * Top bar, ported from final-header/groweire-v7.3 (`header.top`). Right corner: the A+ text-size
 * button (100 / 125 / 150%) and the Find my field button (desing-reference/desired.jpg).
 * Fixed; dark gradient over the hero photo, solid deep green after 70% of a screen of scroll.
 * The link for the section currently in view is underlined in lime.
 * Links point at the matching parts of this page.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Mail } from 'lucide-vue-next'
import GrowEireLogo from '@/components/brand/GrowEireLogo.vue'
import { useTextScale } from '@/composables/useTextScale'

const { cycle, label } = useTextScale()

const links = [
  { to: '/#how-it-works', label: 'How it works', ch: 'how-it-works' },
  { to: '/app', label: 'Check my field', ch: '' },
  { to: '/#coverage', label: 'Field insights', ch: 'coverage' },
  { to: '/#solutions', label: 'Compare rotations', ch: 'solutions' },
  { to: '/#contact', label: 'Contact', ch: 'contact' },
]
const tracked = ['solutions', 'coverage', 'how-it-works', 'contact'] // in page order


const solid = ref(false)
const current = ref('')

function onScroll() {
  solid.value = window.scrollY > window.innerHeight * 0.7
  let cur = ''
  for (const id of tracked) {
    const el = document.getElementById(id)
    if (el && el.getBoundingClientRect().top < window.innerHeight * 0.4) cur = id
  }
  // The contact row is in the footer and never scrolls up that far: at the very bottom, it is current
  const atBottom = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 4
  if (atBottom) cur = 'contact'
  current.value = cur
}

let tick = false
function onScrollRaf() {
  if (tick) return
  tick = true
  requestAnimationFrame(() => {
    tick = false
    onScroll()
  })
}

onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScrollRaf, { passive: true })
})
onBeforeUnmount(() => window.removeEventListener('scroll', onScrollRaf))
</script>

<template>
  <header
    id="top"
    class="top dark"
    :class="{ solid }"
  >
    <div class="wrap">
      <RouterLink
        class="wordmark"
        to="/"
        aria-label="GrowÉire home"
      >
        <GrowEireLogo on-dark />
      </RouterLink>
      <nav aria-label="Main">
        <ol class="navl">
          <li
            v-for="l in links"
            :key="l.label"
          >
            <a
              v-if="l.ch"
              :href="l.to"
              :aria-current="current === l.ch"
            >{{ l.label }}</a>
            <RouterLink
              v-else
              :to="l.to"
            >
              {{ l.label }}
            </RouterLink>
          </li>
        </ol>
      </nav>
      <div style="display:flex;gap:.6rem;align-items:center">
        <!-- Contact for narrow screens, where the nav links (with "Contact") are hidden -->
        <a
          href="/#contact"
          class="aplus contact-btn"
          aria-label="Contact"
          title="Contact"
        >
          <Mail
            class="size-5"
            aria-hidden="true"
          />
        </a>
        <button
          type="button"
          class="aplus"
          :aria-label="label"
          @click="cycle"
        >
          A+
        </button>
        <RouterLink
          to="/app"
          class="btn btn-primary btn-sm find"
        >
          Find my field
        </RouterLink>
      </div>
    </div>
  </header>
</template>

<style scoped>
/* Top bar (v7.3) */
.top {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  z-index: 50;
  color: #ffffff;
  background: linear-gradient(180deg, rgba(5, 17, 13, 0.82) 0%, rgba(5, 17, 13, 0.5) 60%, rgba(5, 17, 13, 0) 100%);
  transition: background-color 0.3s;
}
.top.solid {
  background: #0c2019;
  border-bottom: 1px solid rgba(246, 245, 239, 0.22);
}
.top .wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-height: 4.5rem;
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 3rem;
}
.dark :focus-visible { outline-color: #c8f36b; }

/* Wordmark (v7.3) */
.wordmark {
  display: inline-flex;
  align-items: center;
  min-height: 3rem;
  font-family: 'Manrope', system-ui, sans-serif;
  font-weight: 600;
  font-size: 1.5rem;
  letter-spacing: -0.04em;
  line-height: 1;
  text-decoration: none;
  color: inherit;
}
/* the header sets the size (smaller at big text sizes on phones) */
.wordmark :deep(.ge-logo) { font-size: inherit; }

/* Links (v7.3) */
.navl {
  display: flex;
  gap: 0.25rem;
  list-style: none;
  margin: 0;
  padding: 0;
}
.navl a {
  display: flex;
  align-items: center;
  min-height: 3rem;
  padding: 0 0.9rem;
  text-decoration: none;
  font-weight: 700;
  font-size: 1.0625rem;
  color: inherit;
  border-bottom: 2px solid transparent;
}
.navl a[aria-current='true'] { border-bottom-color: #c8f36b; }

/* A+ and Find my field (reference: desing-reference/desired.jpg) */
.aplus {
  min-width: 3.25rem;
  min-height: 3rem;
  margin: 0 0.25rem;
  border-radius: 999px;
  border: 2px solid currentColor;
  background: transparent;
  color: inherit;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.0625rem;
  cursor: pointer;
  transition: background-color 0.18s;
}
.aplus:hover { background: rgba(246, 245, 239, 0.16); }
.find { white-space: nowrap; }
.contact-btn {
  display: none;
  align-items: center;
  justify-content: center;
  text-decoration: none;
}

@media (max-width: 1060px) {
  .top .wrap { padding: 0 1.25rem; }
  .top nav { display: none; }
  .contact-btn { display: inline-flex; }
}
/* Phones: logo, ✉, A+ and "Find my field" must fit on one row */
@media (max-width: 480px) {
  .top .wrap { padding: 0 0.875rem; gap: 0.5rem; }
  .top .wrap > div { gap: 0.375rem !important; }
  .wordmark { font-size: 1.3rem; }
  .aplus { min-width: 2.75rem; min-height: 2.75rem; margin: 0; font-size: 1rem; }
  .find { padding: 0 0.85rem; }
}
/* The very smallest phones: no room for ✉ (the contact row is still at the foot of the page) */
@media (max-width: 340px) {
  .contact-btn { display: none !important; }
}
@media (max-width: 370px) {
  .top .wrap { gap: 0.5rem; }
  .aplus { margin: 0; }
  .find { padding: 0 0.8rem; }
}
</style>

<style>
/* Unscoped on purpose: keys off the A+ text-size class on <html>.
   Larger text needs more room, so the links collapse earlier and the bar never wraps. */
@media (max-width: 1360px) {
  html.text-125 header.top nav { display: none; }
  html.text-125 header.top .contact-btn { display: inline-flex; }
}
@media (max-width: 1640px) {
  html.text-150 header.top nav { display: none; }
  html.text-150 header.top .contact-btn { display: inline-flex; }
}
/* Small phones at large text: keep the header controls at their 100% size so they fit;
   the rest of the page still scales */
@media (max-width: 520px) {
  html:is(.text-125, .text-150) header.top .wrap { min-height: 72px; padding: 0 20px; gap: 12px; }
  html:is(.text-125, .text-150) header.top .wordmark { min-height: 48px; font-size: 24px; }
  html:is(.text-125, .text-150) header.top .aplus { min-width: 52px; min-height: 48px; font-size: 17px; }
  html:is(.text-125, .text-150) header.top .find { min-height: 48px; padding: 0 17.6px; font-size: 17px; border-width: 2px; }
}
@media (max-width: 370px) {
  html:is(.text-125, .text-150) header.top .wrap { padding: 0 12px; gap: 8px; }
  html:is(.text-125, .text-150) header.top .wordmark { font-size: 21px; }
  html:is(.text-125, .text-150) header.top .aplus { margin: 0; }
  html:is(.text-125, .text-150) header.top .find { padding: 0 12.8px; }
}
</style>

