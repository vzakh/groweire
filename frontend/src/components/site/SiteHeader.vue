<script setup lang="ts">
/**
 * Homepage header, ported from header-reference/groweire (site-header.over):
 * a floating glass pill, fixed to the top. Transparent glass over the hero; once the page
 * scrolls it fills with solid forest (the reference's dark header colour). On narrow screens (and at large text sizes)
 * the links collapse into a full-screen menu.
 */
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import GrowEireLogo from '@/components/brand/GrowEireLogo.vue'
import { useTextScale } from '@/composables/useTextScale'

const { percent, cycle, label } = useTextScale()

const links = [
  { to: '/#how-it-works', label: 'How it works' },
  { to: '/#the-science', label: 'The science' },
  { to: '/app?farm=sample', label: 'Sample farm' },
]

const menuOpen = ref(false)
const menuBtn = ref<HTMLButtonElement | null>(null)
const menuEl = ref<HTMLElement | null>(null)
const closeBtn = ref<HTMLButtonElement | null>(null)

async function openMenu() {
  menuOpen.value = true
  document.body.style.overflow = 'hidden'
  await nextTick()
  closeBtn.value?.focus()
}

function closeMenu(returnFocus = true) {
  if (!menuOpen.value) return
  menuOpen.value = false
  document.body.style.overflow = ''
  if (returnFocus) nextTick(() => menuBtn.value?.focus())
}

/** Keep Tab inside the open menu; Escape closes it. */
function onMenuKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    e.preventDefault()
    closeMenu()
    return
  }
  if (e.key !== 'Tab' || !menuEl.value) return
  const items = menuEl.value.querySelectorAll<HTMLElement>('a[href], button:not([disabled])')
  if (!items.length) return
  const first = items[0]!
  const last = items[items.length - 1]!
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault()
    first.focus()
  }
}

/* Transparent at the top of the page, solid once scrolled */
const scrolled = ref(false)
const onScroll = () => { scrolled.value = window.scrollY > 24 }
onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
})

const route = useRoute()
watch(() => route.fullPath, () => closeMenu(false))
onBeforeUnmount(() => {
  document.body.style.overflow = ''
  window.removeEventListener('scroll', onScroll)
})
</script>

<template>
  <header
    class="site-header on-dark"
    :class="{ 'is-scrolled': scrolled }"
  >
    <nav
      class="nav"
      aria-label="Main"
    >
      <RouterLink
        to="/"
        class="logo-link"
        aria-label="GrowÉire home"
      >
        <GrowEireLogo on-dark />
      </RouterLink>

      <div class="nav-links">
        <RouterLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="nl"
        >
          {{ link.label }}
        </RouterLink>
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
          class="btn btn-primary btn-sm"
        >
          Find my field
        </RouterLink>
      </div>

      <button
        ref="menuBtn"
        type="button"
        class="menu-btn"
        :aria-expanded="menuOpen"
        aria-controls="mobile-menu"
        @click="openMenu"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.4"
          aria-hidden="true"
        ><path d="M4 7h16M4 12h16M4 17h16" /></svg>
        Menu
      </button>
    </nav>
  </header>

  <Teleport to="body">
    <div
      v-if="menuOpen"
      id="mobile-menu"
      ref="menuEl"
      class="mobile-menu on-dark"
      role="dialog"
      aria-modal="true"
      aria-label="Menu"
      @keydown="onMenuKeydown"
    >
      <div class="mm-top">
        <RouterLink
          to="/"
          class="logo-link"
          aria-label="GrowÉire home"
        >
          <GrowEireLogo on-dark />
        </RouterLink>
        <button
          ref="closeBtn"
          type="button"
          class="menu-btn menu-btn--close"
          @click="closeMenu()"
        >
          Close
        </button>
      </div>
      <RouterLink
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        class="ml"
      >
        {{ link.label }}
      </RouterLink>
      <RouterLink
        to="/app"
        class="ml"
      >
        Find my field
      </RouterLink>
      <div class="mm-text">
        <button
          type="button"
          class="aplus"
          :aria-label="label"
          @click="cycle"
        >
          A+
        </button>
        <span>Text size: {{ percent }}</span>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
/* Floating glass pill over the hero (reference: .site-header.over) */
.site-header {
  position: fixed;
  inset: 0 0 auto;
  z-index: 40;
  padding: 1rem var(--hero-pad) 0;
  color: #ffffff;
  pointer-events: none; /* only the pill itself takes clicks */
}
/* Soft top shade only while the header floats over the hero photo */
.site-header::before {
  content: '';
  position: absolute;
  inset: 0 0 -2rem;
  z-index: -1;
  background: linear-gradient(180deg, rgba(11, 29, 23, 0.55), rgba(11, 29, 23, 0));
  transition: opacity 0.3s ease-out;
  pointer-events: none;
}
.site-header.is-scrolled::before { opacity: 0; }
.nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem 1.5rem;
  max-width: calc(var(--hero-wrap) - 2 * var(--hero-pad));
  margin: 0 auto;
  padding: 0.5rem 0.6rem 0.5rem 1.1rem;
  border-radius: 999px;
  background: rgba(11, 29, 23, 0.38);
  border: 1px solid rgba(246, 245, 239, 0.22);
  -webkit-backdrop-filter: blur(14px) saturate(1.2);
  backdrop-filter: blur(14px) saturate(1.2);
  pointer-events: auto;
  transition: background-color 0.3s ease-out, border-color 0.3s ease-out, box-shadow 0.3s ease-out;
}
/* Scrolled: solid forest pill, same contents */
.is-scrolled .nav {
  background: rgba(11, 29, 23, 0.96);
  border-color: rgba(246, 245, 239, 0.14);
  box-shadow: 0 12px 32px -14px rgba(11, 29, 23, 0.6);
}
.logo-link {
  display: inline-flex;
  align-items: center;
  min-height: 3rem;
  border-radius: 999px;
  text-decoration: none;
  color: inherit;
}
.nav-links {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
.nl {
  display: inline-flex;
  align-items: center;
  min-height: 3rem;
  padding: 0 1.1rem;
  border-radius: 999px;
  font-weight: 700;
  font-size: 1.0625rem;
  text-decoration: none;
  color: inherit;
  transition: background-color 0.18s;
}
.nl:hover { background: rgba(246, 245, 239, 0.16); }

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

.menu-btn {
  display: none;
  align-items: center;
  gap: 0.5rem;
  min-height: 3rem;
  padding: 0 0.9rem;
  margin-left: auto;
  border-radius: 999px;
  border: 2px solid currentColor;
  background: transparent;
  color: inherit;
  font-family: var(--font-sans);
  font-weight: 700;
  font-size: 1.0625rem;
  cursor: pointer;
}
.menu-btn--close { display: inline-flex; margin-left: 0; }

/* Full-screen menu (reference: .mobile-menu.open) */
.mobile-menu {
  position: fixed;
  inset: 0;
  z-index: 50;
  overflow: auto;
  padding: 1.25rem;
  background: var(--color-forest-night);
  color: #ffffff;
}
.mm-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}
.ml {
  display: flex;
  align-items: center;
  min-height: 3.75rem;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.5rem;
  text-decoration: none;
  color: inherit;
  border-bottom: 1px solid #2b4a3e;
}
.mm-text {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1.5rem;
}
.mm-text .aplus { margin: 0; }

/* Collapse: 960px at 100% text, later at larger text sizes so the pill never wraps */
@media (max-width: 960px) {
  .nav-links { display: none; }
  .menu-btn { display: inline-flex; }
  .site-header { padding-top: 0.75rem; }
  .nav { padding: 0.4rem 0.4rem 0.4rem 0.9rem; }
}
@media (max-width: 1200px) {
  html.text-125 .nav-links { display: none; }
  html.text-125 .menu-btn { display: inline-flex; }
}
@media (max-width: 1440px) {
  html.text-150 .nav-links { display: none; }
  html.text-150 .menu-btn { display: inline-flex; }
}
</style>
