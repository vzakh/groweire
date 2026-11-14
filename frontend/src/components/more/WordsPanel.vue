<script setup lang="ts">
import { onMounted } from 'vue'
import ErrorState from '@/components/common/ErrorState.vue'
import { Skeleton } from '@/components/ui/skeleton'
import { copy } from '@/copy/en'
import { useCatalogStore } from '@/stores/catalog'

/**
 * "What the words mean": the API's glossary. The farmer's words come first and the technical
 * term follows in brackets. The last entry explains satellite data next to ground data.
 */
const catalog = useCatalogStore()
onMounted(() => catalog.loadGlossary())
</script>

<template>
  <div class="flex flex-col gap-5">
    <h1
      id="panel-title"
      tabindex="-1"
      class="font-heading text-2xl leading-tight font-bold text-balance"
    >
      {{ copy.more.words.label }}
    </h1>

    <ErrorState
      v-if="catalog.glossaryError"
      :error="catalog.glossaryError"
      @retry="catalog.loadGlossary()"
    />
    <div
      v-else-if="!catalog.glossary"
      role="status"
      :aria-label="copy.loading"
      class="flex flex-col gap-3"
    >
      <Skeleton
        v-for="n in 4"
        :key="n"
        class="h-16"
      />
    </div>
    <dl
      v-else
      class="flex flex-col gap-4"
    >
      <div
        v-for="term in catalog.glossary.terms"
        :key="term.id"
        data-test="term"
        class="border-b pb-4 text-base"
      >
        <dt class="text-lg font-bold">
          {{ term.title }}
          <span class="font-normal">({{ term.term }})</span>
        </dt>
        <dd>{{ term.text }}</dd>
      </div>
    </dl>
  </div>
</template>
