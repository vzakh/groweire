<script setup lang="ts">
import { CircleAlertIcon } from '@lucide/vue'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { copy } from '@/copy/en'
import type { FriendlyError } from '@/lib/api'

/** Something failed: say what happened and what to do next, and never blame the person. */
defineProps<{
  error: FriendlyError
  /** Label for the button; without it there is no button. */
  action?: string
}>()
defineEmits<{ retry: [] }>()
</script>

<template>
  <Alert role="alert">
    <CircleAlertIcon aria-hidden="true" />
    <AlertTitle class="text-base font-bold">
      {{ error.message }}
    </AlertTitle>
    <AlertDescription class="flex flex-col items-start gap-3 text-base text-foreground">
      <p>{{ error.next }}</p>
      <Button
        v-if="action !== ''"
        variant="outline"
        size="tap"
        @click="$emit('retry')"
      >
        {{ action ?? copy.retry }}
      </Button>
    </AlertDescription>
  </Alert>
</template>
