<script setup lang="ts">
/**
 * A titled row of data sources, evenly spaced. Each tile shows the source's name and what it
 * gives us (no official logos: we may not use them). Tapping a tile opens a one-line note on
 * what the source is used for.
 */
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

export interface Source {
  name: string
  /** what the source gives us, in two or three words */
  tag: string
  what: string
}

defineProps<{ title: string; items: Source[] }>()
</script>

<template>
  <div class="strip">
    <h3 class="font-display text-[1.25rem] font-bold tracking-[-0.02em] text-forest">
      {{ title }}
    </h3>
    <ul
      class="strip-list"
      :style="{ '--n': items.length }"
    >
      <li
        v-for="s in items"
        :key="s.name"
      >
        <Popover>
          <PopoverTrigger
            class="src"
            :aria-label="`${s.name}: what we use it for`"
          >
            <span class="src-name">{{ s.name }}</span>
            <span class="src-tag">{{ s.tag }}</span>
          </PopoverTrigger>
          <PopoverContent
            class="w-72 rounded-2xl border-hairline p-4"
            :side-offset="6"
          >
            <p class="font-display text-[1.0625rem] font-bold text-forest">
              {{ s.name }}
            </p>
            <p class="mt-1 text-[1rem] leading-snug text-muted-ink">
              {{ s.what }}
            </p>
          </PopoverContent>
        </Popover>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.strip {
  height: 100%;
  padding: 1.75rem 1.75rem 1.5rem;
  border-radius: 20px;
  border: 1px solid var(--color-hairline);
  background: #ffffff;
  box-shadow: 0 10px 30px -20px rgba(18, 43, 35, 0.35);
}
.strip-list {
  display: grid;
  grid-template-columns: repeat(var(--n), minmax(0, 1fr));
  gap: 0.75rem;
  margin: 1.5rem 0 0;
  padding: 0;
  list-style: none;
}
@media (max-width: 640px) {
  .strip-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.src {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  width: 100%;
  height: 100%;
  min-height: 5.5rem;
  padding: 0.85rem 0.5rem;
  border-radius: 14px;
  border: 1.5px solid var(--color-hairline);
  background: var(--color-mist);
  text-align: center;
  cursor: pointer;
  transition: border-color 0.18s, background-color 0.18s, transform 0.2s var(--ease-out-expo);
}
.src:hover,
.src[data-state='open'] {
  border-color: var(--color-emerald);
  background: var(--color-mint);
}
.src-name {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.0625rem;
  line-height: 1.15;
  letter-spacing: -0.01em;
  color: var(--color-forest);
  overflow-wrap: anywhere;
}
.src-tag {
  font-size: 0.875rem;
  line-height: 1.25;
  color: var(--color-muted-ink);
}
@media (hover: hover) {
  .src:hover { transform: translateY(-2px); }
}
</style>
