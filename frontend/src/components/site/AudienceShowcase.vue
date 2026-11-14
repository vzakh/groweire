<script setup lang="ts">
/**
 * Section 2 · Headline + 3 audience scenario cards.
 */
import { ClipboardCheck, Satellite, Tractor } from 'lucide-vue-next'

const cards = [
  {
    id: 'for-growers',
    title: 'For those who grow',
    text: 'Spot your riskiest summer month, cut bare-winter soil months, and compare 3+ practical crop rotations before you buy seed.',
    img: '/img/fields.jpg',
    pos: '50% 70%',
    icon: Tractor,
  },
  {
    id: 'for-advisers',
    title: 'For those who advise',
    text: 'Walk into every farm visit with pre-computed NASA weather history, Teagasc rotation checks, and a 1-page printable adviser summary.',
    img: '/img/reveal-natural.jpg',
    pos: '30% 40%',
    icon: ClipboardCheck,
  },
  {
    id: 'for-catchments',
    title: 'For regional & catchment teams',
    text: 'Track soil-moisture anomalies, winter cover-crop adoption, and water-quality run-off risk across entire Irish river catchments.',
    img: '/img/ireland-sat.jpg',
    pos: '60% 60%',
    icon: Satellite,
  },
] as const
</script>

<template>
  <section
    id="solutions"
    class="bg-mist py-20 lg:py-28"
    aria-labelledby="s2-title"
  >
    <div class="page-wrap">
      <header class="mx-auto max-w-[52rem] text-center">
        <h2
          id="s2-title"
          class="h-section text-forest"
        >
          Satellite intelligence for Irish farming,
          <span class="text-emerald">made simple.</span>
        </h2>
        <p class="mx-auto mt-5 max-w-[44rem] text-[1.1875rem] text-muted-ink">
          From individual tillage fields in Carlow and Westmeath to advisory visits and regional catchment monitoring—built on 45 years of NASA Earth observations.
        </p>
      </header>

      <ul class="mt-12 grid list-none gap-4 p-0 md:grid-cols-3">
        <li
          v-for="c in cards"
          :id="c.id"
          :key="c.id"
          class="aud-card"
        >
          <img
            :src="c.img"
            alt=""
            class="aud-img"
            :style="{ objectPosition: c.pos }"
            loading="lazy"
          >
          <span
            class="aud-scrim"
            aria-hidden="true"
          />
          <div class="relative flex h-full flex-col p-5">
            <span class="inline-flex size-11 items-center justify-center rounded-full bg-white/95 text-forest">
              <component
                :is="c.icon"
                class="size-5"
                aria-hidden="true"
              />
            </span>
            <h3 class="mt-auto font-display text-[1.375rem] leading-tight font-bold tracking-[-0.02em] text-white">
              {{ c.title }}
            </h3>
            <p class="mt-2 text-[1rem] leading-snug text-white/90">
              {{ c.text }}
            </p>
          </div>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.aud-card {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  min-height: 17rem;
  border-radius: 16px;
  background: var(--color-forest);
}
.aud-img {
  position: absolute;
  inset: 0;
  z-index: -2;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.aud-scrim {
  position: absolute;
  inset: 0;
  z-index: -1;
  /* Darkest forest ink (#0B1D17), not black, per the no-black rule */
  background: linear-gradient(180deg, rgba(11, 29, 23, 0.1) 0%, rgba(11, 29, 23, 0.45) 30%, rgba(11, 29, 23, 0.88) 55%, rgba(11, 29, 23, 0.97) 100%);
}
</style>
