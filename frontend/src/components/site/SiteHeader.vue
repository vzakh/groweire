<script setup lang="ts">
/**
 * Top bar, ported from final-header/groweire-v7.3 (`header.top`). The right corner shows the
 * user profile (nickname + picture) from config/assets.ts.
 * Fixed; dark gradient over the hero photo, solid deep green after 70% of a screen of scroll.
 * The link for the section currently in view is underlined in lime.
 * Links point at the matching parts of this page.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { CURRENT_USER } from '@/config/assets'

const initials = CURRENT_USER.nickname.trim().split(' ').filter(Boolean).map((w) => w.charAt(0)).join('').slice(0, 2).toUpperCase()

const links = [
  { to: '/#how-it-works', label: 'How it works', ch: 'how-it-works' },
  { to: '/app', label: 'Check my field', ch: '' },
  { to: '/#coverage', label: 'Field insights', ch: 'coverage' },
  { to: '/#solutions', label: 'Compare rotations', ch: 'solutions' },
]
const tracked = ['solutions', 'coverage', 'how-it-works'] // in page order


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
        <RouterLink
          class="user"
          to="/app"
          :aria-label="`Your profile: ${CURRENT_USER.nickname}`"
        >
          <img
            v-if="CURRENT_USER.avatar"
            class="avatar"
            :src="CURRENT_USER.avatar"
            alt=""
          >
          <span
            v-else
            class="avatar avatar--initials"
            aria-hidden="true"
          >{{ initials }}</span>
          <span
            class="nick"
            aria-hidden="true"
          >{{ CURRENT_USER.nickname }}</span>
        </RouterLink>
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

/* User profile (right corner) */
.user {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  min-height: 3rem;
  padding: 0 1rem 0 0.4rem;
  border-radius: 999px;
  border: 2px solid rgba(255, 255, 255, 0.6);
  background: rgba(5, 17, 13, 0.35);
  color: inherit;
  font-family: 'Atkinson Hyperlegible', system-ui, sans-serif;
  font-weight: 700;
  font-size: 1rem;
  text-decoration: none;
  white-space: nowrap;
  transition: border-color 0.18s;
}
.user:hover { border-color: #ffffff; }
.avatar {
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 999px;
  object-fit: cover;
  flex: 0 0 auto;
}
.avatar--initials {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #c8f36b;
  color: #122b23;
  font-family: 'Manrope', system-ui, sans-serif;
  font-size: 0.875rem;
  font-weight: 700;
}

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
}
@media (max-width: 640px) {
  .top .top-cta { display: none !important; }
}
@media (max-width: 380px) {
  .user { padding-right: 0.4rem; }
  .user .nick { display: none; }
}
</style>

