<script setup lang="ts">
/**
 * Section 6 · Footer. Deep forest, never black.
 * Links only point at things that exist; external data sources open in a new tab.
 */
import { RouterLink } from 'vue-router'
import { ArrowUp, ArrowUpRight, ExternalLink } from 'lucide-vue-next'
import GrowEireLogo from '@/components/brand/GrowEireLogo.vue'

const columns = [
  {
    title: 'Product',
    links: [
      { label: 'Find my field', to: '/app' },
      { label: 'Sample farm', to: '/app?farm=sample' },
    ],
  },
  {
    title: 'Learn',
    links: [
      { label: 'Who it\'s for', to: '/#solutions' },
      { label: 'Coverage', to: '/#coverage' },
      { label: 'How it works', to: '/#how-it-works' },
    ],
  },
  {
    title: 'Data sources',
    links: [
      { label: 'NASA Earthdata', href: 'https://www.earthdata.nasa.gov/' },
      { label: 'Met Éireann', href: 'https://www.met.ie/' },
      { label: 'Teagasc', href: 'https://www.teagasc.ie/' },
    ],
  },
] as const

function backToTop() {
  const calm = document.documentElement.classList.contains('is-static')
    || window.matchMedia('(prefers-reduced-motion: reduce)').matches
  window.scrollTo({ top: 0, behavior: calm ? 'instant' : 'smooth' })
  document.getElementById('main')?.focus({ preventScroll: true })
}
</script>

<template>
  <footer
    class="site-footer on-dark"
    aria-labelledby="footer-title"
  >
    <div class="page-wrap">
      <!-- Closing statement -->
      <div class="grid items-end gap-8 border-b border-white/12 pt-20 pb-14 lg:grid-cols-12 lg:pt-24 lg:pb-16">
        <div class="lg:col-span-7">
          <h2
            id="footer-title"
            class="font-display text-[clamp(2.25rem,4vw,3.5rem)] leading-[1.02] font-semibold tracking-[-0.04em] text-balance text-white"
          >
            Simple answers first.<br>
            <span class="text-lime">Farmer judgment always.</span>
          </h2>
          <p class="mt-5 max-w-[36rem] text-[1.125rem] leading-relaxed text-white/75">
            Global science. Local roots. This tool supports, not replaces, your judgment and local agronomic advice.
          </p>
        </div>
        <div class="flex flex-col gap-3 sm:flex-row sm:flex-wrap lg:col-span-5 lg:justify-end">
          <RouterLink
            to="/app"
            class="btn btn-primary btn-arrow"
          >
            Find my field
            <span
              class="ar"
              aria-hidden="true"
            ><ArrowUpRight class="size-5" /></span>
          </RouterLink>
          <RouterLink
            to="/app?farm=sample"
            class="btn btn-ghost-light"
          >
            Try a sample farm
          </RouterLink>
        </div>
      </div>

      <!-- Brand + link columns -->
      <div class="grid gap-10 py-14 sm:grid-cols-2 lg:grid-cols-12">
        <div class="sm:col-span-2 lg:col-span-4">
          <RouterLink
            to="/"
            class="inline-flex min-h-12 items-center rounded-full"
            aria-label="GrowÉire home"
          >
            <GrowEireLogo on-dark />
          </RouterLink>
          <p class="mt-4 max-w-[26rem] text-[1rem] leading-relaxed text-white/70">
            Crop-rotation planning for Irish farms, built on NASA Earth observations and Irish agricultural guidance.
          </p>
          <div class="mt-8">
            <img
              src="/brand/space-apps-2026.png"
              alt="NASA Space Apps Challenge 2026"
              width="440"
              height="172"
              class="h-auto w-[11rem]"
            >
            <p class="mt-3 max-w-[26rem] text-[0.9375rem] leading-relaxed text-white/65">
              Built at NASA Space Apps Challenge 2026, Hack Athlone. Uses openly available NASA data; not endorsed by NASA.
            </p>
          </div>
        </div>

        <nav
          v-for="col in columns"
          :key="col.title"
          :class="col.title === 'Data sources' ? 'lg:col-span-4' : 'lg:col-span-2'"
          :aria-label="col.title"
        >
          <h3 class="text-[0.9375rem] font-bold tracking-[0.04em] text-lime uppercase">
            {{ col.title }}
          </h3>
          <ul class="mt-3 flex flex-col p-0">
            <li
              v-for="l in col.links"
              :key="l.label"
              class="list-none"
            >
              <a
                v-if="'href' in l"
                :href="l.href"
                target="_blank"
                rel="noopener noreferrer"
                class="f-link"
              >
                {{ l.label }}
                <ExternalLink
                  class="size-4 opacity-70"
                  aria-hidden="true"
                />
                <span class="sr-only">(opens in a new tab)</span>
              </a>
              <RouterLink
                v-else
                :to="l.to"
                class="f-link"
              >
                {{ l.label }}
              </RouterLink>
            </li>
          </ul>
        </nav>
      </div>

      <!-- Bottom bar -->
      <div class="flex flex-col gap-4 border-t border-white/12 py-6 sm:flex-row sm:items-center sm:justify-between">
        <p class="text-[0.9375rem] leading-relaxed text-white/65">
          © 2026 GrowÉire · Uses openly available NASA Earth observation data and Teagasc rotation guidance.
        </p>
        <button
          type="button"
          class="f-link shrink-0 self-start sm:self-auto"
          @click="backToTop"
        >
          Back to top
          <ArrowUp
            class="size-4"
            aria-hidden="true"
          />
        </button>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.site-footer {
  background:
    radial-gradient(50rem 26rem at 0% 0%, rgba(22, 163, 74, 0.16), transparent 60%),
    radial-gradient(40rem 24rem at 100% 100%, rgba(49, 93, 115, 0.22), transparent 60%),
    #0b1d17;
  color: #ffffff;
}
.f-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 3rem;
  color: rgba(255, 255, 255, 0.88);
  font-size: 1.0625rem;
  text-decoration: none;
  text-underline-offset: 0.25em;
  cursor: pointer;
  transition: color 0.18s;
}
.f-link:hover {
  color: var(--color-lime);
  text-decoration: underline;
}
</style>
