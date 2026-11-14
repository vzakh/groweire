<script setup lang="ts">
/**
 * Top bar, ported from final-header/groweire-v7.3 (`header.top`), including the A+ text-size
 * toolbar (100 / 125 / 150 / 200%, remembered in localStorage).
 * Fixed; dark gradient over the hero photo, solid deep green after 70% of a screen of scroll.
 * The link for the section currently in view is underlined in lime.
 * Links point at the matching parts of this page.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

const links = [
  { to: '/#how-it-works', label: 'How it works', ch: 'how-it-works' },
  { to: '/app', label: 'Check my field', ch: '' },
  { to: '/#coverage', label: 'Field insights', ch: 'coverage' },
  { to: '/#solutions', label: 'Compare rotations', ch: 'solutions' },
]
const tracked = ['solutions', 'coverage', 'how-it-works'] // in page order

/* A+ text size (v7.3): 100 → 125 → 150 → 200 → 100 */
const TSZ = ['', 'text-125', 'text-150', 'text-200']
const TLB = ['100%', '125%', '150%', '200%']
const ti = ref(0)
function setText() {
  const h = document.documentElement
  h.classList.remove('text-125', 'text-150', 'text-200')
  if (TSZ[ti.value]) h.classList.add(TSZ[ti.value]!)
}
function cycleText() {
  ti.value = (ti.value + 1) % 4
  try { localStorage.setItem('ge73-ts', String(ti.value)) } catch { /* not persisted */ }
  setText()
}

const solid = ref(false)
const current = ref('')

function onScroll() {
  solid.value = window.scrollY > window.innerHeight * 0.7
  let cur = ''
  for (const id of tracked) {
    const el = document.getElementById(id)
    if (el && el.getBoundingClientRect().top < window.innerHeight * 0.4) cur = id
  }
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
  try { ti.value = parseInt(localStorage.getItem('ge73-ts') || '0', 10) || 0 } catch { ti.value = 0 }
  if (ti.value < 0 || ti.value > 3) ti.value = 0
  setText()
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
        <span aria-hidden="true">Grow</span><span
          class="e"
          aria-hidden="true"
        >E<svg
          viewBox="0 0 40 16"
          preserveAspectRatio="none"
        ><path
          d="M6 15 C14 10 24 5 34 3"
          stroke="#C8F36B"
          stroke-width="4"
          fill="none"
          stroke-linecap="round"
        /><circle
          cx="35"
          cy="3"
          r="3.2"
          fill="#C8F36B"
        /></svg></span><span aria-hidden="true">ire</span>
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
        <button
          id="aplus"
          type="button"
          class="aplus"
          :aria-label="`Text size ${TLB[ti]}. Make text bigger`"
          @click="cycleText"
        >
          <span
            class="ic"
            aria-hidden="true"
          >A+</span><span
            class="tx"
            aria-hidden="true"
          >Text size <span id="ts-val">{{ TLB[ti] }}</span></span>
        </button>
        <RouterLink
          class="btn btn-primary top-cta"
          to="/app"
        >
          Check my field
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
.wordmark .e { position: relative; }
.wordmark .e svg {
  position: absolute;
  left: 10%;
  top: -0.36em;
  width: 95%;
  height: 0.4em;
  overflow: visible;
}

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

/* A+ text-size toolbar (v7.3) */
.aplus {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 3rem;
  border-radius: 999px;
  border: 2px solid rgba(255, 255, 255, 0.6);
  background: rgba(5, 17, 13, 0.35);
  color: inherit;
  font-family: 'Atkinson Hyperlegible', system-ui, sans-serif;
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  padding: 0 1rem 0 0.4rem;
  white-space: nowrap;
}
.aplus .ic {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 999px;
  background: #ffffff;
  color: #122b23;
  font-family: 'Manrope', system-ui, sans-serif;
  font-size: 0.95rem;
}
.aplus:hover { border-color: #ffffff; }

/* Header button (v7.3: shown only when the links collapse) */
.top .top-cta { display: none; }

@media (max-width: 1060px) {
  .top .wrap { padding: 0 1.25rem; }
  .top nav { display: none; }
  .top .top-cta {
    display: inline-flex;
    min-height: 3rem;
    padding: 0 1rem;
    font-size: 1rem;
  }
  .top .aplus .tx { display: inline; }
}
@media (max-width: 640px) {
  .top .top-cta { display: none !important; }
}
</style>

<style>
/* Unscoped on purpose: these key off the A+ text-size class on <html> (v7.3 rules). */
/* Larger text needs more room: collapse the links earlier so the bar never wraps */
header.top .navl a { white-space: nowrap; }
@media (max-width: 1340px) { html.text-125 header.top nav { display: none; } }
@media (max-width: 1620px) { html.text-150 header.top nav { display: none; } }
@media (max-width: 2600px) { html.text-200 header.top nav { display: none; } }
@media (max-width: 400px) { html.text-125 header.top .aplus .tx { display: none; } }
@media (max-width: 1060px) {
  html.text-150 header.top .top-cta,
  html.text-200 header.top .top-cta { display: none; }
}
@media (max-width: 640px) {
  html.text-150 header.top .aplus .tx,
  html.text-200 header.top .aplus .tx { display: none; }
  html.text-200 header.top .wordmark { font-size: 1.05rem; }
  html.text-200 header.top .wrap { gap: 0.5rem; }
}
</style>
