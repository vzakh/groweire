<script setup lang="ts">
/**
 * Section 3 · Two-row country flag marquee, then the stat strip.
 * Flags come from the `flag-icons` package (MIT): drawn SVGs, since Windows can't render flag emoji.
 */
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import IrishFlag from '@/components/brand/IrishFlag.vue'
import StatBlock from './StatBlock.vue'

const flagUrls = import.meta.glob('/node_modules/flag-icons/flags/4x3/{ie,be,fr,dk,at,de,fi,ca,it,se,pl,nl,es,ua,us}.svg', {
  eager: true,
  query: '?url',
  import: 'default',
}) as Record<string, string>
const flag = (code: string) => flagUrls[`/node_modules/flag-icons/flags/4x3/${code}.svg`]

interface Country { code: string; name: string }
const rows: Country[][] = [
  [
    { code: 'be', name: 'Belgium' }, { code: 'fr', name: 'France' }, { code: 'dk', name: 'Denmark' },
    { code: 'ie', name: 'Ireland' }, { code: 'at', name: 'Austria' }, { code: 'de', name: 'Germany' },
    { code: 'fi', name: 'Finland' },
  ],
  [
    { code: 'ca', name: 'Canada' }, { code: 'it', name: 'Italy' }, { code: 'se', name: 'Sweden' },
    { code: 'pl', name: 'Poland' }, { code: 'nl', name: 'Netherlands' }, { code: 'es', name: 'Spain' },
    { code: 'ua', name: 'Ukraine' }, { code: 'us', name: 'United States' },
  ],
]

const note = (c: Country) =>
  c.code === 'ie'
    ? {
        title: 'Ireland · first country pack',
        body: 'NASA Earth observations plus Irish crops, Teagasc rotation guidance and checks against Met Éireann stations.',
      }
    : {
        title: `${c.name} · NASA data available`,
        body: 'The same NASA data covers this country. A local pack with its crops, rules and advisers comes next.',
      }
</script>

<template>
  <section
    id="coverage"
    class="overflow-hidden bg-white py-20 lg:py-24"
    aria-labelledby="s3-title"
  >
    <!-- Flag marquee -->
    <div>
      <h2
        id="s3-title"
        class="h-section page-wrap mx-auto max-w-[56rem] text-center text-forest"
      >
        Built on global NASA Earth observations across
        <span class="text-emerald">180+ countries</span>
        — tailored for
        <span class="text-emerald">Irish fields and advisers</span>
        <IrishFlag class="ml-3 inline-block align-[0.05em]" />
      </h2>

      <div
        class="marquee mt-10 flex flex-col gap-3"
        data-allow-overflow
      >
        <div
          v-for="(row, ri) in rows"
          :key="ri"
          class="marquee-row"
          :class="{ 'is-reverse': ri === 1 }"
        >
          <ul
            v-for="copy in 4"
            :key="copy"
            class="marquee-track"
            :class="{ 'is-copy': copy > 1 }"
            :aria-hidden="copy > 1 ? 'true' : undefined"
          >
            <li
              v-for="c in row"
              :key="c.code"
            >
              <Popover>
                <PopoverTrigger
                  class="flag-pill"
                  :class="{ 'is-home': c.code === 'ie' }"
                  :tabindex="copy > 1 ? -1 : undefined"
                  :aria-label="`${c.name}: how GrowÉire works here`"
                >
                  <img
                    :src="flag(c.code)"
                    alt=""
                    class="h-[1.1em] w-[1.45em] rounded-[3px] object-cover ring-1 ring-forest/10"
                  >
                  {{ c.name }}
                </PopoverTrigger>
                <PopoverContent
                  class="w-72 rounded-2xl border-hairline p-4"
                  :side-offset="8"
                >
                  <p class="font-display text-[1.0625rem] font-bold text-forest">
                    {{ note(c).title }}
                  </p>
                  <p class="mt-1.5 text-[1rem] leading-snug text-muted-ink">
                    {{ note(c).body }}
                  </p>
                </PopoverContent>
              </Popover>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div class="page-wrap mt-20 lg:mt-24">
      <h2 class="sr-only">
        GrowÉire in numbers
      </h2>
      <div class="stats flex flex-wrap justify-center gap-x-8 gap-y-10">
        <StatBlock
          :from="1981"
          :to="2026"
          prefix="1981–"
          text="Continuous daily weather & rainfall records via NASA POWER & GPM"
        />
        <StatBlock
          :to="6"
          unit="NASA Missions"
          text="MODIS, Landsat, SMAP, GPM IMERG, ECOSTRESS & SRTM fused"
        />
        <StatBlock
          :from="10"
          :to="30"
          prefix="10–"
          suffix=" m"
          text="Field-level slope & vegetation detail for parcels from 0.5 ha"
        />
        <StatBlock
          :to="3"
          suffix="+"
          unit="Rotations"
          text="Side-by-side 4-year crop calendars ranked by your priorities"
        />
        <StatBlock
          word="Free"
          text="No account needed to explore your field and compare rotations"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
/* Stats: 1 / 2 / 3 / 5 per row; an incomplete last row is centred */
.stats > * { flex: 0 0 100%; min-width: 0; }
@media (min-width: 640px) { .stats > * { flex-basis: calc((100% - 2rem) / 2); } }
@media (min-width: 1024px) { .stats > * { flex-basis: calc((100% - 4rem) / 3); } }
@media (min-width: 1280px) { .stats > * { flex-basis: calc((100% - 8rem) / 5); } }

.marquee {
  -webkit-mask-image: linear-gradient(90deg, transparent, #fff 8%, #fff 92%, transparent);
  mask-image: linear-gradient(90deg, transparent, #fff 8%, #fff 92%, transparent);
}
.marquee-row {
  display: flex;
  width: max-content;
  animation: marquee 48s linear infinite;
}
.marquee-row.is-reverse {
  animation-direction: reverse;
  animation-duration: 56s;
}
.marquee-row:hover,
.marquee-row:focus-within { animation-play-state: paused; }
@keyframes marquee {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}
.marquee-track {
  display: flex;
  gap: 0.85rem;
  margin: 0;
  padding: 0.5rem 0.425rem;
  list-style: none;
}
.flag-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  min-height: 3rem;
  padding: 0 1.1rem;
  border-radius: 999px;
  border: 1.5px solid var(--color-hairline);
  background: #ffffff;
  box-shadow: 0 2px 10px rgba(18, 43, 35, 0.06);
  color: var(--color-forest);
  font-weight: 700;
  font-size: 1.0625rem;
  white-space: nowrap;
  cursor: pointer;
  transition: border-color 0.18s, background-color 0.18s;
}
.flag-pill:hover,
.flag-pill[data-state='open'] {
  border-color: var(--color-emerald);
  background: var(--color-mint);
}
.flag-pill.is-home {
  border: 2px solid var(--color-emerald);
  background: var(--color-mint);
}

/* Four copies per row; -50% = two copies, which is always wider than the screen, so the loop never shows a gap */

/* Reduced motion and ?static=1: no gliding; each row wraps and centres instead */
@media (prefers-reduced-motion: reduce) {
  .marquee { -webkit-mask-image: none; mask-image: none; }
  .marquee-row { width: auto; justify-content: center; animation: none; }
  .marquee-track { flex-wrap: wrap; justify-content: center; }
  .marquee-track.is-copy { display: none; }
}
html.is-static .marquee { -webkit-mask-image: none; mask-image: none; }
html.is-static .marquee-row { width: auto; justify-content: center; animation: none; }
html.is-static .marquee-track { flex-wrap: wrap; justify-content: center; }
html.is-static .marquee-track.is-copy { display: none; }
</style>
