<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronDownIcon } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { copy } from '@/copy/en'
import type { Schemas } from '@/lib/api'

/**
 * "Your soil": the API's plain facts (drainage, soil mix, acidity, slope) with no judgement,
 * the reminder that these are map estimates and not a soil test, and the numbers one tap away.
 */
const props = defineProps<{
  soil: Schemas['Soil']
  /** The API's "this is not a soil test" sentence, when it sent one. */
  gap?: string
}>()

const open = ref(false)

const rows = computed(() => {
  const labels = copy.answer.soil.rows
  return (Object.keys(labels) as (keyof typeof labels)[])
    .map((key) => ({ key, label: labels[key], value: props.soil[key] }))
    .filter((row) => row.value !== null && row.value !== undefined)
})
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle class="font-heading text-xl font-bold">
        {{ copy.answer.soil.title }}
      </CardTitle>
    </CardHeader>
    <CardContent class="flex flex-col gap-3">
      <dl
        v-if="soil.plain?.length"
        class="flex flex-col gap-2"
      >
        <div
          v-for="fact in soil.plain"
          :key="fact.label"
          data-test="soil-fact"
          class="text-base"
        >
          <dt class="font-bold">
            {{ fact.label }}
          </dt>
          <dd>{{ fact.text }}</dd>
        </div>
      </dl>
      <p
        v-if="gap"
        class="border-l-4 border-border pl-3 text-base"
      >
        {{ gap }}
      </p>

      <Collapsible v-model:open="open">
        <CollapsibleTrigger as-child>
          <Button
            variant="outline"
            size="tap"
            class="w-full justify-between"
          >
            {{ copy.answer.soil.numbers }}
            <ChevronDownIcon
              data-icon="inline-end"
              :class="{ 'rotate-180': open }"
            />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent class="flex flex-col gap-3 pt-4">
          <Badge
            variant="outline"
            class="h-auto px-3 py-1 text-base"
          >
            {{ copy.source }}: {{ copy.answer.soil.sources[soil.source] }}
          </Badge>
          <dl class="flex flex-col gap-1">
            <div
              v-for="row in rows"
              :key="row.key"
              class="flex justify-between gap-4 border-b py-1 text-base"
            >
              <dt>{{ row.label }}</dt>
              <dd class="font-bold tabular-nums">
                {{ row.value }}
              </dd>
            </div>
          </dl>
        </CollapsibleContent>
      </Collapsible>
    </CardContent>
  </Card>
</template>
