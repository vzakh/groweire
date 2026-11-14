import { computed, ref, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import { api, unwrap, useResource, type Schemas } from '@/lib/api'
import { areaHa as cornersAreaHa, circlePolygon, polygonFromCorners, type LngLat, type Polygon } from '@/lib/geo'

export const DEFAULT_AREA_HA = 10
/** Limits the API enforces for any field. */
export const MIN_AREA_HA = 0.1
export const MAX_AREA_HA = 2000
export const MAX_CORNERS = 500

/**
 * Finding and placing the field (step 1), and the field the API then gives back with its
 * conditions (soil, climate, satellite greenness).
 */
export const useFieldStore = defineStore('field', () => {
  // --- place search -------------------------------------------------------------------
  const places = useResource<Schemas['PlacesOut']>()
  /** The search the current results belong to. */
  const searched = ref('')
  const place = shallowRef<Schemas['Place'] | null>(null)

  /** One request per submit: no search-as-you-type (the place service allows 1 request a second). */
  function search(text: string) {
    const q = text.trim()
    if (q.length < 2) return
    searched.value = q
    return places.run(() => unwrap(api.GET('/api/v1/places', { params: { query: { q } } })))
  }

  function choosePlace(result: Schemas['Place']) {
    place.value = result
  }

  // --- placing ------------------------------------------------------------------------
  const point = shallowRef<LngLat | null>(null)
  const areaHa = ref(DEFAULT_AREA_HA)
  /** Corners tapped while drawing the field's edges. */
  const corners = shallowRef<LngLat[]>([])
  const drawing = ref(false)
  /** Show the satellite photo under the map while placing the field. */
  const satellite = ref(false)

  function setPoint(next: LngLat) {
    point.value = next
  }
  function setArea(next: number) {
    areaHa.value = Math.min(MAX_AREA_HA, Math.max(MIN_AREA_HA, next))
  }
  /** Put a 10 ha field on the place that was searched for: the path with no map tapping. */
  function usePlace() {
    if (!place.value) return
    point.value = [place.value.lon, place.value.lat]
    areaHa.value = DEFAULT_AREA_HA
  }

  function startDrawing() {
    drawing.value = true
    corners.value = []
    point.value = null
  }
  function addCorner(corner: LngLat) {
    if (corners.value.length < MAX_CORNERS) corners.value = [...corners.value, corner]
  }
  function undoCorner() {
    corners.value = corners.value.slice(0, -1)
  }
  function stopDrawing() {
    drawing.value = false
    corners.value = []
  }
  function clearPlacement() {
    point.value = null
    stopDrawing()
  }

  const drawnAreaHa = computed(() => cornersAreaHa(corners.value))
  const hasDrawing = computed(() => drawing.value && corners.value.length >= 3)
  /** True once there is something to send: a point, or at least three drawn corners. */
  const hasPlacement = computed(() => hasDrawing.value || (!drawing.value && point.value !== null))

  /** What the map shows before the field exists: the drawn shape, or a circle of the chosen size. */
  const preview = computed<Polygon | null>(() => {
    if (hasDrawing.value) return polygonFromCorners(corners.value)
    if (!drawing.value && point.value) return circlePolygon(point.value, areaHa.value)
    return null
  })

  // --- the field ----------------------------------------------------------------------
  const field = useResource<Schemas['FieldOut']>()
  const conditions = useResource<Schemas['ConditionsOut']>()

  /** Create the field from what was placed. Resolves the new field, or null on failure. */
  async function create(): Promise<Schemas['FieldOut'] | null> {
    const body: Schemas['FieldCreate'] = hasDrawing.value
      ? { geometry: polygonFromCorners(corners.value) }
      : { point: point.value, area_ha: areaHa.value }
    if (place.value) body.name = `Near ${place.value.name.split(',')[0]}`
    const created = await field.run(() => unwrap(api.POST('/api/v1/fields', { body })))
    if (created) {
      conditions.reset()
      clearPlacement()
    }
    return created
  }

  /** Make sure the field with this id is loaded: a no-op after `create`, a fetch on a shared link. */
  function ensure(id: string) {
    if (field.data.value?.field_id === id || field.loading.value) return
    conditions.reset()
    return field.run(() =>
      unwrap(api.GET('/api/v1/fields/{field_id}', { params: { path: { field_id: id } } })),
    )
  }

  function loadConditions(id: string) {
    if (conditions.data.value?.field_id === id || conditions.loading.value) return
    return conditions.run(() =>
      unwrap(api.GET('/api/v1/fields/{field_id}/conditions', { params: { path: { field_id: id } } })),
    )
  }

  function forget() {
    field.reset()
    conditions.reset()
  }

  return {
    places: places.data,
    placesLoading: places.loading,
    placesError: places.error,
    searched,
    place,
    search,
    choosePlace,
    point,
    areaHa,
    corners,
    drawing,
    satellite,
    setPoint,
    setArea,
    usePlace,
    startDrawing,
    addCorner,
    undoCorner,
    stopDrawing,
    clearPlacement,
    drawnAreaHa,
    hasDrawing,
    hasPlacement,
    preview,
    field: field.data,
    fieldLoading: field.loading,
    fieldError: field.error,
    conditions: conditions.data,
    conditionsLoading: conditions.loading,
    conditionsError: conditions.error,
    create,
    ensure,
    loadConditions,
    forget,
  }
})
