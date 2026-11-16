<script setup lang="ts">
/**
 * Section 6 · Footer. Deep forest, never black.
 * Links only point at things that exist; external data sources open in a new tab.
 */
import { RouterLink } from 'vue-router'
import { ArrowUp, ArrowUpRight, Check, Copy, ExternalLink, Github, Mail } from 'lucide-vue-next'
import { ref } from 'vue'
import GrowEireLogo from '@/components/brand/GrowEireLogo.vue'
import { OWNER, TEAM } from '@/config/owner'

/** Copy the email address (a mailto: link does nothing for people without a mail app set up). */
const copied = ref(false)
async function copyEmail() {
  try {
    await navigator.clipboard.writeText(OWNER.email)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    // clipboard refused: the address is visible in the link and the tooltip
  }
}

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

      <!-- Owner: one quiet line, who runs this copy and how to reach them -->
      <div
        id="contact"
        class="owner flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-white/12 py-5">
        <p class="text-[0.9375rem] text-white/75">
          This version is built and maintained by
          <a
            :href="OWNER.github"
            class="owner-name"
            target="_blank"
            rel="noopener"
          >@{{ OWNER.handle }}</a>
        </p>
        <ul
          class="flex flex-wrap items-center gap-2"
          aria-label="Contact"
        >
          <li>
            <a
              :href="OWNER.repo"
              class="badge"
              target="_blank"
              rel="noopener"
            >
              <Github
                class="size-4"
                aria-hidden="true"
              />
              Source code
            </a>
          </li>
          <li>
            <a
              :href="OWNER.github"
              class="badge"
              target="_blank"
              rel="noopener"
            >
              <Github
                class="size-4"
                aria-hidden="true"
              />
              GitHub
            </a>
          </li>
          <li class="inline-flex">
            <a
              :href="`mailto:${OWNER.email}`"
              class="badge badge--start"
              :title="OWNER.email"
            >
              <Mail
                class="size-4"
                aria-hidden="true"
              />
              Email
            </a>
            <button
              type="button"
              class="badge badge--end"
              :aria-label="copied ? 'Email address copied' : `Copy email address ${OWNER.email}`"
              :title="copied ? 'Copied' : 'Copy email address'"
              @click="copyEmail"
            >
              <component
                :is="copied ? Check : Copy"
                class="size-4"
                aria-hidden="true"
              />
            </button>
          </li>
        </ul>
        <p class="w-full text-[0.875rem] text-white/55 lg:ml-auto lg:w-auto">
          Started at {{ TEAM.event }} with
          <a
            :href="TEAM.repo"
            class="underline underline-offset-4 hover:text-[var(--color-lime)]"
            target="_blank"
            rel="noopener"
          >{{ TEAM.name }}</a>
        </p>
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
/* Clear the fixed top bar when the nav's "Contact" link scrolls here */
.owner { scroll-margin-top: 6rem; }
.owner-name {
  color: #ffffff;
  font-weight: 700;
  text-decoration: none;
}
.owner-name:hover { color: var(--color-lime); text-decoration: underline; text-underline-offset: 0.25em; }
/* Compact social badges: outlined pills, lime on hover */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 2.5rem;
  padding: 0 0.85rem;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 999px;
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.9375rem;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  background: transparent;
  transition: border-color 0.18s, color 0.18s, background-color 0.18s;
}
.badge--start { border-radius: 999px 0 0 999px; }
/* The copy button sits joined to the right of Email, as one split pill */
.badge--end { border-radius: 0 999px 999px 0; border-left: 0; padding: 0 0.7rem 0 0.6rem; }
.badge:hover { border-color: var(--color-lime); color: var(--color-lime); background: rgba(200, 243, 107, 0.06); }
.badge:focus-visible, .owner-name:focus-visible { outline: 2px solid var(--color-lime); outline-offset: 2px; }

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
