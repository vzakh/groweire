<script setup lang="ts">
/**
 * A titled row of source logos, evenly spaced. Each logo opens a one-line note on what the
 * source is used for. Logo files and their licence status: public/logos/SOURCES.md.
 */
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

export interface Source {
  name: string
  logo: string
  /** optional visual scale for wide wordmarks, 0–1 of the tile height */
  scale?: number
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
            <span class="src-logo">
              <img
                :src="s.logo"
                alt=""
                :style="s.scale ? { maxHeight: `${s.scale * 100}%` } : undefined"
              >
            </span>
            <span class="src-name">{{ s.name }}</span>
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
  .strip-list { grid-template-columns: repeat(3, minmax(0, 1fr)); row-gap: 1.25rem; }
}
.src {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
  min-height: 3rem;
  padding: 0.25rem;
  border-radius: 14px;
  cursor: pointer;
}
.src-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 4.25rem;
  transition: transform 0.2s var(--ease-out-expo);
}
.src-logo img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.src-name {
  font-weight: 700;
  font-size: 0.9375rem;
  line-height: 1.2;
  text-align: center;
  color: var(--color-forest);
}
@media (hover: hover) {
  .src:hover .src-logo { transform: translateY(-3px); }
}
</style>
