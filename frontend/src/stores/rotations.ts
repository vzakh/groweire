import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api, unwrap, useResource, type Schemas } from '@/lib/api'
import { buildCompareBody } from '@/lib/answers'
import { useFlowStore } from './flow'

/** The farmer's rotation compared with the alternatives the API suggests. */
export const useRotationsStore = defineStore('rotations', () => {
  const flow = useFlowStore()
  const compared = useResource<Schemas['CompareOut']>()
  /** The request the loaded comparison answers, so changed answers trigger a new one. */
  const loadedFor = ref('')

  const body = computed(() => (flow.fieldId ? buildCompareBody(flow.fieldId, flow.answers) : null))

  /** Compare for the current answers. A no-op when that comparison is already loaded, unless forced. */
  async function compare(force = false) {
    if (!body.value) return
    const key = JSON.stringify(body.value)
    if (!force && key === loadedFor.value && (compared.data.value || compared.loading.value)) return
    loadedFor.value = key
    const request = body.value
    await compared.run(() => unwrap(api.POST('/api/v1/rotations/compare', { body: request })))
  }

  /** The comparison, only while it still matches the answers in the URL. */
  const result = computed(() =>
    body.value && JSON.stringify(body.value) === loadedFor.value ? compared.data.value : null,
  )

  return { body, result, loading: compared.loading, error: compared.error, compare }
})
