<script setup lang="ts">
/**
 * GrowÉire wordmark, the same one as the landing page header (final-header/groweire-v7.3):
 * "GrowEire" with a lime sprout over the E standing in for the fada.
 * White text on dark backgrounds (`onDark`), forest green on light ones. The sprout stays lime.
 * Size follows `--ge-logo-size` (default 1.5rem), or `font-size` set on the logo itself.
 */
withDefaults(defineProps<{ onDark?: boolean }>(), { onDark: false })
</script>

<template>
  <span
    class="ge-logo"
    :class="{ 'ge-logo--dark': onDark }"
    role="img"
    aria-label="GrowÉire"
  >
    <span aria-hidden="true">Grow</span><span
      class="ge-logo__e"
      aria-hidden="true"
    >E<svg
      viewBox="0 0 40 16"
      preserveAspectRatio="none"
      focusable="false"
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
  </span>
</template>

<style scoped>
.ge-logo {
  display: inline-block;
  white-space: nowrap;
  font-family: 'Manrope', system-ui, sans-serif;
  font-weight: 600;
  font-size: var(--ge-logo-size, 1.5rem);
  letter-spacing: -0.04em;
  line-height: 1;
  color: var(--color-forest);
}
.ge-logo--dark { color: #ffffff; }
.ge-logo__e { position: relative; }
.ge-logo__e svg {
  position: absolute;
  left: 10%;
  top: -0.36em;
  width: 95%;
  height: 0.4em;
  overflow: visible;
}
</style>
