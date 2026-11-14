<script setup lang="ts">
/**
 * Homepage hero, ported exactly from final-header/groweire-v7.3 (`section.home`).
 * Links point at this site: "Check my field" → /app, "Explore an example farm" → the sample farm.
 * Motion (photo settle, line draw, headline rise) is frozen by style.css for reduced motion / ?static=1.
 */
import { RouterLink } from 'vue-router'
import { HERO_IMAGE, HERO_IMAGE_ALT } from '@/config/assets'
</script>

<template>
  <section
    id="home"
    class="home dark"
    aria-labelledby="h-home"
  >
    <img
      class="bg"
      :src="HERO_IMAGE"
      :alt="HERO_IMAGE_ALT"
      fetchpriority="high"
    >
    <div
      class="scrim"
      aria-hidden="true"
    />
    <div
      class="vgrid"
      aria-hidden="true"
    >
      <span /><span /><span /><span />
    </div>
    <svg
      class="lines draw"
      viewBox="0 0 1440 900"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
      style="opacity:.5"
    >
      <path d="M-20 220 C220 160 420 260 640 210 C860 160 1040 90 1460 150" />
      <path d="M-20 252 C230 196 430 292 650 244 C870 196 1050 128 1460 186" />
      <path d="M-20 284 C240 232 440 324 660 278 C880 232 1060 166 1460 222" />
    </svg>
    <div class="home-inner">
      <div class="wrap">
        <p class="kicker">
          Global science · Local roots
        </p>
        <h1
          id="h-home"
          class="h-home"
          style="margin-top:1rem"
        >
          <span class="rise"><span>Know your land.</span></span><span class="rise"><span>Grow your future.</span></span>
        </h1>
        <p
          class="lead"
          style="margin-top:1.5rem;max-width:min(38rem,100%)"
        >
          Compare crop rotations using NASA Earth observations and your farming knowledge.
        </p>
        <div class="hero-cta">
          <RouterLink
            class="btn btn-primary"
            to="/app"
          >
            Check my field <span
              class="ar"
              aria-hidden="true"
            >→</span>
          </RouterLink>
          <RouterLink
            id="explore-example"
            class="link"
            to="/app?farm=sample"
          >
            Explore an example farm
          </RouterLink>
        </div>
        <ol
          class="hsteps"
          aria-label="How GrowÉire works"
        >
          <li>
            <span
              class="n"
              aria-hidden="true"
            >1</span><span>Answer three short questions about one field</span>
          </li>
          <li>
            <span
              class="n"
              aria-hidden="true"
            >2</span><span>See what satellite data shows for your area</span>
          </li>
          <li>
            <span
              class="n"
              aria-hidden="true"
            >3</span><span>Compare your rotation with two alternatives</span>
          </li>
        </ol>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* All values from final-header/groweire-v7.3 */
.dark {
  background: #0c2019;
  color: #ffffff;
}
.dark :focus-visible { outline-color: #c8f36b; }

.home {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}
.home .bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  animation: settle 16s ease-out both;
}
@keyframes settle {
  from { transform: scale(1.06); }
  to { transform: none; }
}
.home .scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(12, 32, 25, 0.45) 0%, rgba(12, 32, 25, 0.08) 32%, rgba(12, 32, 25, 0.55) 66%, rgba(12, 32, 25, 0.92) 100%);
}

/* Vertical grid */
.vgrid {
  position: absolute;
  inset: 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  pointer-events: none;
}
.vgrid span { border-left: 1px solid rgba(255, 255, 255, 0.1); }

/* Lines */
.lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.lines path {
  fill: none;
  stroke: #fff;
  stroke-width: 1.1;
  vector-effect: non-scaling-stroke;
}
.lines.draw path {
  stroke-dasharray: 3000;
  stroke-dashoffset: 3000;
  animation: draw 3.2s cubic-bezier(0.2, 0.7, 0.2, 1) forwards;
}
.lines.draw path:nth-child(2) { animation-delay: 0.25s; }
.lines.draw path:nth-child(3) { animation-delay: 0.5s; }
@keyframes draw { to { stroke-dashoffset: 0; } }

.home-inner {
  position: relative;
  padding: 8rem 0 3rem;
}
.wrap {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 3rem;
}

.kicker {
  font-weight: 700;
  font-size: 0.9375rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #c8f36b;
}
.h-home {
  margin: 0;
  font-family: 'Manrope', system-ui, sans-serif;
  font-weight: 500;
  font-size: clamp(3rem, 7.4vw, 7.5rem);
  letter-spacing: -0.055em;
  line-height: 0.95;
  color: inherit;
}
.rise {
  display: block;
  overflow: hidden;
  padding-bottom: 0.05em;
}
.rise > span {
  display: block;
  animation: rise 1s cubic-bezier(0.2, 0.7, 0.2, 1) both;
}
.rise:nth-child(2) > span { animation-delay: 0.12s; }
@keyframes rise {
  from { transform: translateY(105%); }
  to { transform: none; }
}
.lead {
  font-size: 1.25rem;
  line-height: 1.5;
}

.hero-cta {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  flex-wrap: wrap;
  margin-top: 1.75rem;
}
.hero-cta .btn {
  gap: 0.6rem;
  min-height: 3.5rem;
  padding: 0 1.6rem;
  font-size: 1.125rem;
  line-height: 1.2;
  text-align: center;
}
.btn .ar {
  display: inline-flex;
  transition: transform 0.2s cubic-bezier(0.2, 0.7, 0.2, 1);
}
.btn:hover .ar { transform: translateX(4px); }
.link {
  display: inline-flex;
  align-items: center;
  min-height: 3rem;
  padding: 0;
  font-weight: 700;
  font-size: 1.1875rem;
  text-decoration: underline;
  text-underline-offset: 0.22em;
  color: inherit;
  cursor: pointer;
}

.hsteps {
  list-style: none;
  margin: 2.75rem 0 0;
  padding: 1.5rem 0 0;
  border-top: 1px solid rgba(246, 245, 239, 0.22);
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.5rem;
}
.hsteps li {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  font-size: 1.0625rem;
}
.hsteps .n {
  flex: 0 0 auto;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 999px;
  border: 1.5px solid #c8f36b;
  color: #c8f36b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: 'Manrope', system-ui, sans-serif;
  font-weight: 700;
  font-size: 1rem;
}

@media (max-width: 1060px) {
  .wrap { padding: 0 1.25rem; }
  .h-home { font-size: clamp(2.5rem, 11.5vw, 4rem); }
  .vgrid { grid-template-columns: repeat(2, 1fr); }
  .hsteps {
    grid-template-columns: 1fr;
    gap: 1rem;
    margin-top: 2rem;
  }
  .hero-cta .btn {
    max-width: 100%;
    padding: 0 1.1rem;
  }
}
</style>
