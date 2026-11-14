<script setup lang="ts">
/**
 * Section 4 · How It Works: Data Fusion & Crop Rotation.
 * Top: framed interface screenshot (placeholder until the real UI exists) + 3 steps.
 * Bottom: 4 feature cards straddling the dark/light edge, then the two source strips.
 */
import { ImageIcon, Layers, Leaf, ShieldAlert, UserRound } from 'lucide-vue-next'
import { HOW_IT_WORKS_SCREENSHOT, HOW_IT_WORKS_SCREENSHOT_ALT } from '@/config/assets'
import DataStrip, { type Source } from './DataStrip.vue'

const steps = [
  {
    title: 'Ingest Earth Observations',
    text: 'Combine NASA crop greenness (MODIS & Landsat), root-zone soil moisture (SMAP), rainfall (GPM IMERG), and 30m terrain slope (SRTM) for your area.',
  },
  {
    title: 'Input Local Parameters & Priorities',
    text: 'Enter your last four years of crops and rank what matters most: steady income, less work, keeping winter soil covered, fixing nitrogen, or breaking cereal disease.',
  },
  {
    title: 'Evaluate Rotation Scenarios',
    text: 'Compare your current rotation against at least two tailored alternatives, complete with satellite evidence, Teagasc guidance, data limits, and questions for your adviser.',
  },
]

const features = [
  { icon: Layers, title: 'Environmental Dataset Harmonization', text: 'Rainfall, weather, greenness and terrain from different satellites, lined up on one grid for your area.' },
  { icon: Leaf, title: 'Biomass & Moisture Analysis', text: 'Past crop greenness and soil-moisture records show when crops around you were under stress.' },
  { icon: ShieldAlert, title: 'Risk & Vulnerability Mapping', text: 'Wet sowing windows, dry spells, frost and run-off risk, flagged month by month.' },
  { icon: UserRound, title: 'Farmer-Centered UI', text: 'Plain words, large text and a printable summary to talk through with your adviser.' },
]

const missions: Source[] = [
  { name: 'GPM', tag: 'Rainfall', what: 'Global Precipitation Measurement (IMERG): rainfall estimates, including heavy-rain events.' },
  { name: 'GRACE-FO', tag: 'Groundwater', what: 'Gravity satellites that track long-term changes in stored water and groundwater.' },
  { name: 'Landsat', tag: 'Field images', what: '30 m images: crop greenness and bare-soil periods at field scale.' },
  { name: 'SMAP', tag: 'Soil moisture', what: 'Soil moisture near the surface and in the root zone (regional context, 9 km).' },
  { name: 'ECOSTRESS', tag: 'Plant water use', what: 'Land-surface temperature and evapotranspiration: how much water plants are using.' },
]
const providers: Source[] = [
  { name: 'NASA Earthdata', tag: 'Satellite data', what: 'Where the NASA datasets are published and downloaded.' },
  { name: 'Met Éireann', tag: 'Weather stations', what: 'Irish weather-station records, used to check the satellite estimates on the ground.' },
  { name: 'Teagasc', tag: 'Farm guidance', what: 'Irish rotation guidance and soil information behind the farming advice.' },
]
</script>

<template>
  <section
    id="how-it-works"
    aria-labelledby="s4-title"
  >
    <!-- Dark top -->
    <div class="hiw-dark on-dark pt-20 pb-40 lg:pt-28 lg:pb-48">
      <div class="page-wrap">
        <h2
          id="s4-title"
          class="h-section mx-auto max-w-[62rem] text-center text-white"
        >
          How It Works: <span class="text-lime">Data Fusion</span> &amp; Crop Rotation
        </h2>

        <div class="hiw-top mt-14 grid items-center gap-12 lg:mt-16 lg:grid-cols-12 lg:gap-14">
          <!-- Interface frame -->
          <div class="min-w-0 lg:col-span-7">
            <div class="device">
              <div class="device-bar">
                <span
                  class="flex gap-1.5"
                  aria-hidden="true"
                >
                  <i /><i /><i />
                </span>
                <span class="device-url">groweire.ie/app</span>
              </div>
              <div class="device-screen">
                <img
                  v-if="HOW_IT_WORKS_SCREENSHOT"
                  :src="HOW_IT_WORKS_SCREENSHOT"
                  :alt="HOW_IT_WORKS_SCREENSHOT_ALT"
                  class="size-full object-cover"
                >
                <div
                  v-else
                  class="placeholder"
                  role="img"
                  aria-label="Interface preview placeholder"
                >
                  <div
                    class="ph-sidebar"
                    aria-hidden="true"
                  >
                    <i /><i /><i /><i />
                  </div>
                  <div
                    class="ph-main"
                    aria-hidden="true"
                  >
                    <div class="ph-map" />
                    <div class="ph-row">
                      <i /><i /><i />
                    </div>
                  </div>
                  <div class="ph-label">
                    <ImageIcon
                      class="size-6"
                      aria-hidden="true"
                    />
                    <span>Interface preview</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Steps -->
          <ol class="steps min-w-0 lg:col-span-5">
            <li
              v-for="(s, i) in steps"
              :key="s.title"
              class="step"
            >
              <span
                class="step-n"
                aria-hidden="true"
              >{{ i + 1 }}</span>
              <div>
                <h3 class="font-display text-[1.3125rem] leading-tight font-bold tracking-[-0.02em] text-white">
                  <span class="sr-only">{{ i + 1 }}. </span>{{ s.title }}
                </h3>
                <p class="mt-2 text-[1.0625rem] leading-relaxed text-white/75">
                  {{ s.text }}
                </p>
              </div>
            </li>
          </ol>
        </div>
      </div>
    </div>

    <!-- Light bottom -->
    <div class="flow-root bg-mist-warm pb-20 lg:pb-28">
      <div class="page-wrap">
        <ul class="-mt-28 grid gap-5 p-0 sm:grid-cols-2 xl:grid-cols-4">
          <li
            v-for="f in features"
            :key="f.title"
            class="feature"
          >
            <span class="feature-icon">
              <component
                :is="f.icon"
                class="size-5"
                aria-hidden="true"
              />
            </span>
            <h3 class="mt-5 font-display text-[1.25rem] leading-tight font-bold tracking-[-0.02em] text-balance text-forest">
              {{ f.title }}
            </h3>
            <p class="mt-2.5 text-[1rem] leading-relaxed text-muted-ink">
              {{ f.text }}
            </p>
          </li>
        </ul>

        <div class="mt-6 grid gap-5 lg:grid-cols-[1.45fr_1fr]">
          <DataStrip
            title="Integration"
            :items="missions"
          />
          <DataStrip
            title="Data Providers"
            :items="providers"
          />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hiw-dark {
  background:
    radial-gradient(55rem 32rem at 105% 105%, rgba(215, 181, 120, 0.28), transparent 62%),
    radial-gradient(48rem 30rem at -5% -10%, rgba(49, 93, 115, 0.45), transparent 62%),
    linear-gradient(165deg, #0f3a2c 0%, #122b23 50%, #0b1d17 100%);
}

/* Device frame */
.device {
  overflow: hidden;
  border-radius: 18px;
  background: #f6f5ef;
  box-shadow:
    0 0 0 1px rgba(246, 245, 239, 0.14),
    0 0 0 10px rgba(246, 245, 239, 0.05),
    0 40px 80px -30px rgba(3, 12, 8, 0.75);
}
.device-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.7rem 1rem;
  border-bottom: 1px solid var(--color-hairline);
  background: #ffffff;
}
.device-bar i {
  display: block;
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 999px;
  background: #d6dbd3;
}
.device-url {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 18rem;
  margin: 0 auto;
  padding: 0.2rem 0.75rem;
  border-radius: 999px;
  background: var(--color-mist);
  color: var(--color-muted-ink);
  font-size: 0.9375rem;
  text-align: center;
}
.device-screen {
  position: relative;
  aspect-ratio: 16 / 10;
}

/* Placeholder: a quiet wireframe of the workspace */
.placeholder {
  position: absolute;
  inset: 0;
  display: grid;
  grid-template-columns: 22% 1fr;
  gap: 4%;
  padding: 4%;
  background:
    radial-gradient(circle, rgba(18, 43, 35, 0.07) 1px, transparent 1.2px) 0 0 / 14px 14px,
    #f6f5ef;
}
.ph-sidebar,
.ph-main { display: flex; flex-direction: column; gap: 6%; }
.ph-sidebar i {
  display: block;
  height: 8%;
  border-radius: 8px;
  background: #e4e9e1;
}
.ph-sidebar i:first-child { width: 70%; background: #d6ddd2; }
.ph-map {
  flex: 1;
  border-radius: 12px;
  background:
    linear-gradient(135deg, rgba(22, 163, 74, 0.1), rgba(49, 93, 115, 0.12)),
    #e9eee6;
  border: 1.5px dashed #b9c4b6;
}
.ph-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4%; height: 22%; }
.ph-row i { display: block; border-radius: 10px; background: #e4e9e1; }
@media (max-width: 640px) {
  .ph-label { padding: 0.5rem 0.9rem; font-size: 0.9375rem; }
  .ph-label :deep(svg) { width: 1.1rem; height: 1.1rem; }
}
.ph-label {
  position: absolute;
  left: 50%;
  top: 50%;
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.7rem 1.2rem;
  border-radius: 999px;
  background: #ffffff;
  color: var(--color-forest);
  font-weight: 700;
  font-size: 1.0625rem;
  white-space: nowrap;
  transform: translate(-50%, -50%);
  box-shadow: 0 10px 24px -14px rgba(18, 43, 35, 0.5);
}

/* Steps joined by a rail */
.steps {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 2.25rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
/* Connector from each number to the next one */
.step:not(:last-child)::before {
  content: '';
  position: absolute;
  top: 3.25rem;
  bottom: -1.75rem;
  left: 1.3125rem;
  width: 2px;
  border-radius: 2px;
  background: linear-gradient(180deg, rgba(200, 243, 107, 0.65), rgba(200, 243, 107, 0.2));
}
.step {
  position: relative;
  display: grid;
  grid-template-columns: 2.75rem minmax(0, 1fr);
  gap: 1.25rem;
  overflow-wrap: anywhere; /* long words never push past narrow screens at large text */
}
@media (max-width: 380px) {
  .step { gap: 0.9rem; }
}
.step-n {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 999px;
  background: var(--color-lime);
  color: var(--color-forest);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.125rem;
  box-shadow: 0 0 0 6px #122b23;
}

/* Feature cards overlap the dark/light edge */
.feature {
  list-style: none;
  padding: 1.75rem 1.6rem 1.9rem;
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 22px 44px -26px rgba(11, 29, 23, 0.55);
  transition: transform 0.25s var(--ease-out-expo), box-shadow 0.25s;
}
.feature-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 14px;
  background: var(--color-mint);
  color: var(--color-emerald-press);
}
@media (hover: hover) {
  .feature:hover {
    transform: translateY(-4px);
    box-shadow: 0 28px 50px -26px rgba(11, 29, 23, 0.6);
  }
}
</style>
