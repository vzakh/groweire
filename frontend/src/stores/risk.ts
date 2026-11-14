import { computed, reactive, ref, shallowReactive } from 'vue'
import { defineStore } from 'pinia'
import { api, ApiFailure, toFriendlyError, unwrap, useResource, type FriendlyError, type Schemas } from '@/lib/api'
import { riskCrop } from '@/lib/answers'
import { FIRST_MONTH } from '@/lib/query'
import type { StressType } from '@/lib/risk'
import { useFieldStore } from './field'
import { useFlowStore } from './flow'

/** One risk map: the grid cells for a month, for one weather type or each cell's main type. */
export type RiskLayer = Schemas['StressRiskLayer']

/** What the map should colour right now. */
export interface RiskView {
  month: number
  /** null = each cell's most frequent weather type. */
  type: StressType | null
  /** Faint while the farmer answers steps 2 and 3; full on the answer and on "More maps". */
  strength: 'faint' | 'full'
}

/**
 * The counted monthly risk for the field, and the risk map. The risk is counted from 25 years
 * of weather history; nothing here predicts a coming season.
 */
export const useRiskStore = defineStore('risk', () => {
  const flow = useFlowStore()
  const field = useFieldStore()

  // --- the field's answer -------------------------------------------------------------
  /** Asked right after the field exists, before any crop is known. */
  const general = useResource<Schemas['PredictOut']>()
  /** Asked again once we know what grew here last year. */
  const forCrop = useResource<Schemas['PredictOut']>()

  function predict(fieldId: string, cropId: string | null) {
    const target = cropId ? forCrop : general
    const loaded = target.data.value
    if (loaded && loaded.field_id === fieldId && loaded.crop_id === cropId) return
    return target.run(() =>
      unwrap(
        api.POST('/api/v1/predict/stress-risk', {
          body: { field_id: fieldId, mode: 'seasonal_profile', crop_id: cropId },
        }),
      ),
    )
  }

  /** The answer for the crop grown last year, once it has arrived and still matches. */
  const answer = computed(() => {
    const crop = riskCrop(flow.answers)
    const loaded = forCrop.data.value
    return loaded && loaded.field_id === flow.fieldId && loaded.crop_id === crop ? loaded : null
  })
  const generalAnswer = computed(() =>
    general.data.value?.field_id === flow.fieldId ? general.data.value : null,
  )

  /** The month picked on the answer screen; the riskiest month until one is picked. */
  const selectedMonth = computed(
    () => flow.month ?? answer.value?.riskiest_month ?? generalAnswer.value?.riskiest_month ?? null,
  )

  // --- the risk map -------------------------------------------------------------------
  const layers = shallowReactive(new Map<string, RiskLayer>())
  const layerError = ref<FriendlyError | null>(null)
  const pending = new Map<string, Promise<RiskLayer | null>>()

  const layerKey = (month: number, type: StressType | null) => `${month}|${type ?? ''}`

  /** The risk map for a month, fetched once and kept. */
  function loadLayer(month: number, type: StressType | null): Promise<RiskLayer | null> {
    const key = layerKey(month, type)
    const cached = layers.get(key)
    if (cached) return Promise.resolve(cached)
    const running = pending.get(key)
    if (running) return running

    layerError.value = null
    const request = unwrap<RiskLayer>(
      api.GET('/api/v1/layers/stress-risk', {
        params: { query: { month, type: type ?? undefined } },
      }),
    )
      .then((layer) => {
        layers.set(key, layer)
        return layer
      })
      .catch((thrown: unknown) => {
        layerError.value = thrown instanceof ApiFailure ? thrown.friendly : toFriendlyError(thrown)
        return null
      })
      .finally(() => pending.delete(key))
    pending.set(key, request)
    return request
  }

  /** "More maps": the layer, month and weather type an advisor is looking at. */
  const explore = reactive({
    layerId: 'stress_risk',
    month: FIRST_MONTH,
    type: null as StressType | null,
    /** Day for the satellite layers (YYYY-MM-DD); empty = the layer's newest day. */
    date: '',
  })

  const view = computed<RiskView | null>(() => {
    if (flow.section === 'maps') {
      return explore.layerId === 'stress_risk'
        ? { month: explore.month, type: explore.type, strength: 'full' }
        : null
    }
    if (flow.section || !flow.fieldId) return null
    // Outside Ireland there is no counted grid to show
    if (field.field?.pilot_coverage === false) return null
    if (flow.step === 4) {
      return selectedMonth.value ? { month: selectedMonth.value, type: null, strength: 'full' } : null
    }
    if (flow.step >= 2) {
      const month = generalAnswer.value?.riskiest_month
      return month ? { month, type: null, strength: 'faint' } : null
    }
    return null
  })

  return {
    general: general.data,
    generalError: general.error,
    forCropLoading: forCrop.loading,
    forCropError: forCrop.error,
    predict,
    answer,
    generalAnswer,
    selectedMonth,
    layers,
    layerError,
    layerKey,
    loadLayer,
    explore,
    view,
  }
})
