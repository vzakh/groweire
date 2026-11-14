<script setup lang="ts">
/**
 * GrowÉire logo: the name only, one colour, no icon.
 * White on dark backgrounds (`onDark`), forest green on light ones so it stays visible.
 */
withDefaults(defineProps<{ onDark?: boolean }>(), { onDark: false })
</script>

<template>
  <span
    class="ge-logo"
    :class="{ 'ge-logo--dark': onDark }"
  >GrowÉire</span>
</template>

<style scoped>
.ge-logo {
  display: inline-block;
  white-space: nowrap;
  font-family: var(--font-display);
  font-weight: 700;
  /* shrinks a little on narrow phones so it never pushes the Menu button off-screen */
  font-size: min(1.625rem, 6.4vw);
  letter-spacing: -0.04em;
  line-height: 1.15;
  color: var(--color-forest);
}
.ge-logo--dark { color: #ffffff; }
</style>
