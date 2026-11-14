<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { CopyIcon, MailIcon, MessageCircleIcon, MessageSquareIcon, PrinterIcon, SendIcon } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { copy } from '@/copy/en'
import { canNativeShare, copyLink, nativeShare, shareLinks } from '@/lib/share'
import { router } from '@/router'
import { useFlowStore } from '@/stores/flow'

/**
 * Print the one-page summary, or send the link to an advisor or family. The link carries the
 * field and every answer, so it is also the only "save". Sending opens in place (no pop-up)
 * and says first that the link shows where the field is.
 */
const flow = useFlowStore()

const open = ref(false)
const copied = ref(false)

const printTo = computed(() => ({
  name: 'print',
  params: { id: flow.fieldId ?? '' },
  query: router.currentRoute.value.query,
}))

/** The full address of this answer. */
const url = computed(() => new URL(router.resolve(flow.place({ step: 4, section: null })).href, location.origin).href)
const links = computed(() => shareLinks(copy.share.text, url.value, copy.share.subject))

async function send() {
  // The warning must be read before anything leaves the phone, so the first tap only opens it
  if (!open.value) {
    open.value = true
    return
  }
  await nativeShare(copy.share.subject, copy.share.text, url.value)
}

async function copyUrl() {
  copied.value = await copyLink(url.value)
}
</script>

<template>
  <section class="flex flex-col gap-3">
    <div class="flex gap-2">
      <Button
        as-child
        variant="outline"
        size="tap"
        class="flex-1"
      >
        <RouterLink :to="printTo">
          <PrinterIcon data-icon="inline-start" />
          {{ copy.share.print }}
        </RouterLink>
      </Button>
      <Button
        variant="outline"
        size="tap"
        class="flex-1"
        :aria-expanded="open"
        data-test="send"
        @click="open ? (open = false) : send()"
      >
        <SendIcon data-icon="inline-start" />
        {{ copy.share.send }}
      </Button>
    </div>

    <div
      v-if="open"
      data-test="send-panel"
      class="flex flex-col gap-3 rounded-xl border-2 border-foreground p-4"
    >
      <p class="text-base font-bold">
        {{ copy.share.warning }}
      </p>
      <Button
        v-if="canNativeShare()"
        size="tap"
        @click="send()"
      >
        <SendIcon data-icon="inline-start" />
        {{ copy.share.send }}
      </Button>
      <template v-else>
        <Button
          as-child
          variant="outline"
          size="tap"
          class="justify-start"
        >
          <a
            :href="links.whatsapp"
            target="_blank"
            rel="noopener"
          >
            <MessageCircleIcon data-icon="inline-start" />
            {{ copy.share.whatsapp }}
          </a>
        </Button>
        <Button
          as-child
          variant="outline"
          size="tap"
          class="justify-start"
        >
          <a :href="links.sms">
            <MessageSquareIcon data-icon="inline-start" />
            {{ copy.share.sms }}
          </a>
        </Button>
        <Button
          as-child
          variant="outline"
          size="tap"
          class="justify-start"
        >
          <a :href="links.email">
            <MailIcon data-icon="inline-start" />
            {{ copy.share.email }}
          </a>
        </Button>
      </template>
      <Button
        variant="outline"
        size="tap"
        class="justify-start"
        @click="copyUrl"
      >
        <CopyIcon data-icon="inline-start" />
        {{ copy.share.copy }}
      </Button>
      <p
        v-if="copied"
        role="status"
        class="text-base font-bold"
      >
        {{ copy.share.copied }}
      </p>
    </div>
  </section>
</template>
