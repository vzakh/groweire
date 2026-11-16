<script setup lang="ts">
import { copy } from '@/copy/en'
import { useFieldStore } from '@/stores/field'
import { useFlowStore } from '@/stores/flow'

/**
 * Map / Satellite switch in the map's bottom-right corner, like Google Maps: a small tile that
 * previews the OTHER view and is labelled with it. Tap it to swap. Hidden on "More maps",
 * which has its own layer picker.
 */
const field = useFieldStore()
const flow = useFlowStore()
</script>

<template>
  <button
    v-if="flow.section !== 'maps'"
    type="button"
    class="map-switch absolute right-3 bottom-10 z-10"
    :aria-label="field.satellite ? copy.map.toMapLabel : copy.map.toSatelliteLabel"
    :aria-pressed="field.satellite"
    @click="field.satellite = !field.satellite"
  >
    <img
      v-if="!field.satellite"
      src="/img/map-switch-satellite.jpg"
      alt=""
      width="288"
      height="288"
    >
    <!-- A drawn street-map tile: fields, a river, roads (the basemap is vector, so no image) -->
    <svg
      v-else
      viewBox="0 0 80 80"
      aria-hidden="true"
      focusable="false"
    >
      <rect
        width="80"
        height="80"
        fill="#f4f1ea"
      />
      <path
        d="M0 0h34l-6 26H0z"
        fill="#d8ebc9"
      />
      <path
        d="M52 46h28v34H44z"
        fill="#d8ebc9"
      />
      <path
        d="M58 0c-4 14 6 22 2 36s-14 20-12 44"
        stroke="#a9cbe8"
        stroke-width="6"
        fill="none"
      />
      <path
        d="M0 52 80 34"
        stroke="#ffffff"
        stroke-width="5"
      />
      <path
        d="M0 52 80 34"
        stroke="#f6d27a"
        stroke-width="2.5"
      />
      <path
        d="M22 80 34 0M0 70h44M40 14l40 6"
        stroke="#ffffff"
        stroke-width="3"
        fill="none"
      />
    </svg>
    <span class="map-switch__label">
      {{ field.satellite ? copy.map.toMap : copy.map.toSatellite }}
    </span>
  </button>
</template>

<style scoped>
.map-switch {
  /* big enough to see what the other view looks like; smaller on phones, where the map is short */
  width: 9rem;
  height: 9rem;
  padding: 0;
  overflow: hidden;
  border: 3px solid #ffffff;
  border-radius: 0.75rem;
  background: #ffffff;
  box-shadow: 0 2px 8px rgb(0 0 0 / 0.35);
  cursor: pointer;
}
.map-switch img,
.map-switch svg {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.map-switch__label {
  position: absolute;
  inset: auto 0 0;
  padding: 1.5rem 0.5rem 0.5rem;
  background: linear-gradient(transparent, rgb(0 0 0 / 0.65));
  color: #ffffff;
  font-size: 1.0625rem;
  font-weight: 700;
  line-height: 1;
  text-align: center;
}
@media (max-width: 640px) {
  .map-switch { width: 6.5rem; height: 6.5rem; }
  .map-switch__label { padding: 1.1rem 0.4rem 0.4rem; font-size: 0.9375rem; }
}
.map-switch:hover { box-shadow: 0 3px 12px rgb(0 0 0 / 0.45); }
.map-switch:focus-visible {
  outline: 3px solid var(--color-atlantic);
  outline-offset: 2px;
}
</style>
