<script setup lang="ts">
/**
 * Homepage hero, ported from header-reference/groweire (D01 · Homepage).
 * Copy is the approved current version.
 */
import { RouterLink } from 'vue-router'
import { HERO_IMAGE, HERO_IMAGE_ALT } from '@/config/assets'
</script>

<template>
  <section
    class="hero on-dark"
    aria-labelledby="hero-title"
  >
    <!-- Photo and overlay share one coordinate space and settle together -->
    <div class="hero-media">
      <img
        class="hero-img"
        :src="HERO_IMAGE"
        :alt="HERO_IMAGE_ALT"
        width="2048"
        height="1534"
        fetchpriority="high"
      >
      <svg
        class="geo"
        viewBox="0 0 1800 1348"
        preserveAspectRatio="xMidYMid slice"
        aria-hidden="true"
      >
        <path
          class="draw"
          d="M-20 300 C500 120 1200 80 1830 210"
          pathLength="1"
          fill="none"
          stroke="#FFFFFF"
          stroke-opacity=".6"
          stroke-width="2"
        />
        <g class="fade">
          <circle
            cx="1460"
            cy="128"
            r="9"
            fill="#C8F36B"
          />
          <path
            d="M0 412 L416 400 L600 598 L0 690 Z"
            fill="rgba(200,243,107,.16)"
            stroke="#C8F36B"
            stroke-width="4"
          />
          <path
            d="M416 400 L560 330 L840 330"
            fill="none"
            stroke="#C8F36B"
            stroke-width="2"
          />
          <text
            x="572"
            y="316"
            class="geo-label"
          >A ploughed field: bare soil</text>
        </g>
      </svg>
    </div>
    <div
      class="scrim"
      aria-hidden="true"
    />

    <div class="hero-content">
      <div class="wrap">
        <p class="eyebrow">
          Global science. Local roots.
        </p>
        <h1 id="hero-title">
          <span class="reveal-line"><span>Know your land.</span></span>
          <span class="reveal-line"><span>Grow your future.</span></span>
        </h1>
        <div class="hero-meta">
          <p class="lead">
            Explore smarter crop rotations for your farm with NASA Earth observations and Irish agricultural knowledge.
          </p>
          <div class="hero-ctas">
            <RouterLink
              to="/app"
              class="btn btn-primary btn-arrow"
            >
              Find my field
              <span
                class="ar"
                aria-hidden="true"
              ><svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.4"
              ><path d="M7 17L17 7M9 7h8v8" /></svg></span>
            </RouterLink>
            <RouterLink
              to="/app?farm=sample"
              class="btn btn-ghost-light"
            >
              Try a sample farm
            </RouterLink>
          </div>
        </div>
        <p class="footnote">
          No account needed · Four short steps · You decide
        </p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero {
  position: relative;
  height: 100vh;
  min-height: 45rem; /* 720px at 100% text */
  max-height: 62.5rem; /* 1000px */
  overflow: hidden;
  background: var(--color-forest-night);
}
.hero-media {
  position: absolute;
  inset: 0;
}
.hero-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: 50% 50%;
}
.scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(11, 29, 23, 0.25) 0%,
    rgba(11, 29, 23, 0) 30%,
    rgba(11, 29, 23, 0.35) 55%,
    rgba(11, 29, 23, 0.9) 100%
  );
}
.geo {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.geo-label {
  font-family: var(--font-sans);
  font-weight: 700;
  font-size: 30px;
  fill: #ffffff;
  paint-order: stroke;
  stroke: rgba(11, 29, 23, 0.7);
  stroke-width: 6px;
}

.hero-content {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding-bottom: 3rem;
}
.wrap {
  max-width: var(--hero-wrap);
  margin: 0 auto;
  padding: 0 var(--hero-pad);
}
.eyebrow {
  margin-bottom: 1rem;
  font-weight: 700;
  font-size: 1.0625rem;
  color: var(--color-lime);
}
h1 {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 500;
  font-size: clamp(3.25rem, 6.6vw, 6.25rem);
  line-height: 0.98;
  letter-spacing: -0.05em;
  color: #ffffff;
}
.reveal-line {
  display: block;
  overflow: hidden;
  padding-bottom: 0.06em;
}
.reveal-line > span { display: block; }
.hero-meta {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  column-gap: 1.5rem;
  align-items: end;
  margin-top: 1.75rem;
}
.lead {
  grid-column: 1 / span 6;
  font-size: 1.3125rem;
  line-height: 1.5;
  color: #ffffff;
}
.hero-ctas {
  grid-column: 7 / span 6;
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  justify-content: flex-end;
}
.footnote {
  margin-top: 1.25rem;
  font-size: 1rem;
  color: #e6ebe7;
}

/* --- Motion 01: Living Landscape (off for reduced motion and ?static=1, via style.css) --- */
.hero-media { animation: drift 18s ease-out both; }
@keyframes drift {
  from { transform: scale(1.06); }
  to { transform: none; }
}
.reveal-line > span { animation: line-up 0.9s var(--ease-grow) both; }
.reveal-line:nth-child(2) > span { animation-delay: 0.12s; }
@keyframes line-up {
  from { transform: translateY(105%); }
  to { transform: none; }
}
.draw {
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  animation: draw 2.4s var(--ease-grow) 0.3s forwards;
}
@keyframes draw { to { stroke-dashoffset: 0; } }
.fade {
  opacity: 0;
  animation: fade-in 0.8s ease 1.6s forwards;
}
@keyframes fade-in { to { opacity: 1; } }

/* --- Narrow screens (reference breakpoint 960px) --- */
@media (max-width: 960px) {
  /* Content flows instead of sitting absolutely, so large text sizes can't overflow the photo */
  .hero {
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    height: auto;
    min-height: 100svh;
    max-height: none;
    padding-top: 6.5rem; /* clear the floating header */
  }
  .hero-content { position: relative; }
  h1 { font-size: clamp(2.5rem, 11vw, 3.75rem); }
  .fade { display: none; }
  .hero-meta {
    grid-template-columns: 1fr;
    row-gap: 1.25rem;
  }
  .lead,
  .hero-ctas { grid-column: auto; }
  .lead { font-size: 1.1875rem; }
  .hero-ctas { justify-content: stretch; }
  .hero-ctas .btn { flex: 1 1 100%; }
}
</style>
