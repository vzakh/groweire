import { computed, ref, watch } from 'vue'
import type { GeoJSONSource, Map as MapLibreMap, MapMouseEvent, Marker, Popup } from 'maplibre-gl'
import { copy } from '@/copy/en'
import { bboxOf } from '@/lib/geo'
import { RISK_LEVELS, STRESS_TYPES, type RiskLevel, type StressType } from '@/lib/risk'
import { useCatalogStore } from '@/stores/catalog'
import { useFieldStore } from '@/stores/field'
import { useFlowStore } from '@/stores/flow'
import { useRiskStore } from '@/stores/risk'
import { IRELAND, useMap } from './useMap'

/**
 * What the one map shows and does, decided by where the person is:
 *   step 1            tap to mark the field (or its corners); optional satellite photo
 *   steps 2 and 3     the field outline, with the risk squares faint behind it; taps do nothing
 *   step 4            the field outline and the risk squares for the picked month; tap a square
 *   More maps         any NASA layer, or the risk map for any month and weather type
 * Call once, from the app shell.
 */
const EMPTY = { type: 'FeatureCollection', features: [] } as const
const FOREST = '#122b23'
/**
 * Under the satellite photo: NASA Blue Marble Next Generation, a cloud-free picture of the
 * whole Earth (about 500 m). The sharp HLS photo covers only what the satellite saw on its day,
 * so without this the land around it would be the plain street map.
 */
const PHOTO_BACKDROP = {
  tiles:
    'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_NextGeneration/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg',
  maxzoom: 8,
}
const PICTURE_LAYERS = ['picture-base', 'picture'] as const

export function useMapScene() {
  const { map, lib, styleVersion } = useMap()
  const flow = useFlowStore()
  const field = useFieldStore()
  const risk = useRiskStore()
  const catalog = useCatalogStore()

  let marker: Marker | null = null
  let fieldPin: Marker | null = null
  let popup: Popup | null = null

  /** True while a tap on the map marks the field. */
  const placing = computed(() => !flow.section && flow.step === 1)

  /**
   * The NASA picture layer to have on the map, if any. In step 1 the satellite photo is loaded
   * even before it is asked for (see `warm`), so the button only has to make it visible.
   */
  const picture = computed(() => {
    let id: string | null = null
    if (flow.section === 'maps') id = risk.explore.layerId === 'stress_risk' ? null : risk.explore.layerId
    else if (placing.value) id = 'true_colour'
    const layer = id ? catalog.layerById.get(id) : undefined
    if (!layer || layer.kind !== 'gibs_wmts') return null
    const day = (flow.section === 'maps' && risk.explore.date) || layer.time.default
    return {
      id: layer.id,
      key: `${layer.id}|${day}`,
      tiles: layer.url_template.replace('{Time}', day),
      maxzoom: layer.max_zoom ?? 9,
      attribution: layer.attribution,
    }
  })

  /** The map, once a basemap style is in and our layers can be added. */
  function ready(): MapLibreMap | null {
    return styleVersion.value > 0 ? map.value : null
  }

  function setData(source: string, data: unknown) {
    const target = ready()?.getSource(source) as GeoJSONSource | undefined
    target?.setData(data as Parameters<GeoJSONSource['setData']>[0])
  }

  function addLayers(m: MapLibreMap) {
    if (m.getSource('risk')) return
    for (const id of ['risk', 'preview', 'corners', 'field']) {
      m.addSource(id, { type: 'geojson', data: EMPTY as never })
    }
    m.addLayer({
      id: 'risk-fill',
      type: 'fill',
      source: 'risk',
      layout: { visibility: 'none' },
      paint: {
        'fill-color': [
          'match',
          ['get', 'level'],
          'low',
          RISK_LEVELS.low.fill,
          'medium',
          RISK_LEVELS.medium.fill,
          'high',
          RISK_LEVELS.high.fill,
          '#cccccc',
        ],
        'fill-opacity': 0.7,
        'fill-outline-color': 'rgba(255,255,255,0.35)',
      },
    })
    m.addLayer({
      id: 'preview-fill',
      type: 'fill',
      source: 'preview',
      paint: { 'fill-color': '#c8f36b', 'fill-opacity': 0.35 },
    })
    m.addLayer({
      id: 'preview-line',
      type: 'line',
      source: 'preview',
      paint: { 'line-color': FOREST, 'line-width': 3, 'line-dasharray': [2, 1.5] },
    })
    m.addLayer({
      id: 'corners',
      type: 'circle',
      source: 'corners',
      paint: { 'circle-radius': 7, 'circle-color': '#ffffff', 'circle-stroke-color': FOREST, 'circle-stroke-width': 3 },
    })
    m.addLayer({
      id: 'field-casing',
      type: 'line',
      source: 'field',
      paint: { 'line-color': '#ffffff', 'line-width': 7 },
    })
    m.addLayer({
      id: 'field-line',
      type: 'line',
      source: 'field',
      paint: { 'line-color': FOREST, 'line-width': 3.5 },
    })
  }

  // --- risk squares ---------------------------------------------------------------------
  async function showRisk() {
    const m = ready()
    if (!m) return
    const view = risk.view
    popup?.remove()
    if (!view) {
      m.setLayoutProperty('risk-fill', 'visibility', 'none')
      return
    }
    const layer = await risk.loadLayer(view.month, view.type)
    const now = risk.view
    // The person moved on while this was loading
    if (!now || now.month !== view.month || now.type !== view.type) return
    if (!layer || !ready()) return
    setData('risk', layer)
    m.setPaintProperty('risk-fill', 'fill-opacity', view.strength === 'full' ? 0.7 : 0.15)
    m.setLayoutProperty('risk-fill', 'visibility', 'visible')
  }

  // --- NASA picture layer ---------------------------------------------------------------
  /** True when the person should see the picture (not only have it loaded). */
  const pictureShown = computed(() =>
    flow.section === 'maps' ? picture.value !== null : placing.value && field.satellite,
  )

  /**
   * NASA's tile server says "do not cache" (no-store), so every tile is a fresh download.
   * Once the step-1 map has settled, load the photo for the current view at opacity 0;
   * MapLibre keeps those tiles in memory and the button then shows them at once.
   * Skipped when the browser asks to save data or the connection is slow.
   */
  const warm = ref(false)
  function mayPreload(): boolean {
    const c = (navigator as Navigator & {
      connection?: { saveData?: boolean; effectiveType?: string; type?: string }
    }).connection
    if (!c) return true
    return !c.saveData && c.type !== 'cellular' && !['slow-2g', '2g', '3g'].includes(c.effectiveType ?? '')
  }
  function warmWhenIdle() {
    const m = ready()
    if (!m || warm.value || !placing.value || !mayPreload()) return
    // 'idle' fires only after the next render, so check whether the map has settled already
    if (m.loaded() && m.areTilesLoaded()) {
      warm.value = true
      return
    }
    m.once('idle', () => {
      if (placing.value) warm.value = true
    })
  }

  let pictureKey: string | null = null
  function showPicture() {
    const m = ready()
    if (!m) return
    const wanted = picture.value
    // Only rebuild the source when the layer or day changes, so the loaded tiles are kept
    if (!wanted || wanted.key !== pictureKey || !m.getSource('picture')) {
      for (const id of PICTURE_LAYERS) {
        if (m.getLayer(id)) m.removeLayer(id)
        if (m.getSource(id)) m.removeSource(id)
      }
      pictureKey = null
      if (!wanted) return
      if (wanted.id === 'true_colour') {
        m.addSource('picture-base', {
          type: 'raster',
          tiles: [PHOTO_BACKDROP.tiles],
          tileSize: 256,
          maxzoom: PHOTO_BACKDROP.maxzoom,
          attribution: 'NASA Blue Marble',
        })
        m.addLayer(
          {
            id: 'picture-base',
            type: 'raster',
            source: 'picture-base',
            paint: { 'raster-opacity': 0, 'raster-opacity-transition': { duration: 200, delay: 0 } },
          },
          'risk-fill',
        )
      }
      m.addSource('picture', {
        type: 'raster',
        tiles: [wanted.tiles],
        tileSize: 256,
        maxzoom: wanted.maxzoom,
        attribution: wanted.attribution,
      })
      // Under our own layers, over the basemap
      m.addLayer(
        {
          id: 'picture',
          type: 'raster',
          source: 'picture',
          paint: { 'raster-opacity': 0, 'raster-opacity-transition': { duration: 200, delay: 0 } },
        },
        'risk-fill',
      )
      pictureKey = wanted.key
    }
    const shown = pictureShown.value
    // Hidden layers ('none') load nothing; a warm one loads at opacity 0
    for (const id of PICTURE_LAYERS) {
      if (!m.getLayer(id)) continue
      m.setLayoutProperty(id, 'visibility', shown || warm.value ? 'visible' : 'none')
      m.setPaintProperty(id, 'raster-opacity', shown ? 1 : 0)
    }
  }

  // --- the field ------------------------------------------------------------------------
  const outline = computed(() => {
    const current = field.field
    return current && current.field_id === flow.fieldId ? current : null
  })

  /** True while the risk squares are the thing to look at: the answer, and "More maps". */
  const wide = computed(() => risk.view?.strength === 'full')

  function showField() {
    const m = ready()
    if (!m) return
    const current = outline.value
    setData('field', current ? { type: 'Feature', geometry: current.geometry, properties: {} } : EMPTY)
    // A pin as well as the outline: zoomed out to the risk squares, a field is only a few pixels wide
    if (current && lib.value && !placing.value) {
      fieldPin ??= new lib.value.Marker({ color: FOREST })
      fieldPin.setLngLat(current.centroid).addTo(m)
      fieldPin.getElement().setAttribute('aria-label', copy.map.marker)
    } else {
      fieldPin?.remove()
    }
  }

  /**
   * Close on the field while answering questions; pulled back on the answer so the risk
   * squares around it (each about 5 km wide) can be seen and compared.
   */
  function zoomToField() {
    const m = ready()
    const current = outline.value
    const box = current && bboxOf((current.geometry as { coordinates?: unknown }).coordinates)
    if (!m || !current || !box) return
    if (wide.value) m.flyTo({ center: current.centroid, zoom: 9.5, duration: 900 })
    else m.fitBounds([[box[0], box[1]], [box[2], box[3]]], { padding: 90, maxZoom: 13.5, duration: 900 })
  }

  // --- placing (step 1) -----------------------------------------------------------------
  function showPlacement() {
    const m = ready()
    if (!m) return
    const active = placing.value
    setData('preview', active && field.preview ? { type: 'Feature', geometry: field.preview, properties: {} } : EMPTY)
    setData(
      'corners',
      active && field.drawing
        ? {
            type: 'FeatureCollection',
            features: field.corners.map((corner) => ({
              type: 'Feature',
              geometry: { type: 'Point', coordinates: corner },
              properties: {},
            })),
          }
        : EMPTY,
    )
    const at = active && !field.drawing ? field.point : null
    if (at && lib.value) {
      marker ??= new lib.value.Marker({ color: FOREST, scale: 1.4 })
      marker.setLngLat(at).addTo(m)
      marker.getElement().setAttribute('aria-label', copy.map.marker)
    } else {
      marker?.remove()
    }
    m.getCanvas().style.cursor = active ? 'crosshair' : ''
  }

  /** Back to the whole island: where a new field starts. */
  function zoomToIreland() {
    const m = ready()
    if (!m) return
    m.fitBounds([[IRELAND[0], IRELAND[1]], [IRELAND[2], IRELAND[3]]], { padding: 24, duration: 900 })
  }

  function zoomToPlace() {
    const m = ready()
    const target = field.place
    if (!m || !target) return
    const box = target.bbox
    if (box && box.length === 4) {
      m.fitBounds([[box[0]!, box[1]!], [box[2]!, box[3]!]], { padding: 40, maxZoom: 14, duration: 900 })
    } else {
      m.flyTo({ center: [target.lon, target.lat], zoom: 13, duration: 900 })
    }
  }

  // --- taps -----------------------------------------------------------------------------
  function onClick(event: MapMouseEvent) {
    const m = ready()
    if (!m) return
    if (placing.value) {
      const at: [number, number] = [event.lngLat.lng, event.lngLat.lat]
      if (field.drawing) field.addCorner(at)
      else field.setPoint(at)
      return
    }
    if (risk.view?.strength !== 'full' || !lib.value) return
    const cell = m.queryRenderedFeatures(event.point, { layers: ['risk-fill'] })[0]
    if (!cell) return
    const props = cell.properties as {
      level: RiskLevel
      years_hit: number
      years_total: number
      dominant_type?: StressType | null
      stress_type?: StressType | null
    }
    const type = props.stress_type ?? props.dominant_type
    const box = document.createElement('div')
    const title = document.createElement('strong')
    title.textContent = [RISK_LEVELS[props.level]?.word, type ? STRESS_TYPES[type]?.word : null]
      .filter(Boolean)
      .join(' · ')
    const count = document.createElement('div')
    count.textContent = copy.answer.ofYears(props.years_hit, props.years_total)
    box.append(title, count)
    popup?.remove()
    popup = new lib.value.Popup({ maxWidth: '18rem' }).setLngLat(event.lngLat).setDOMContent(box).addTo(m)
  }

  // --- wiring ---------------------------------------------------------------------------
  watch(map, (m, previous) => {
    if (m && !previous) m.on('click', onClick)
  })

  // A new basemap style drops every layer we added: put them all back
  watch(styleVersion, () => {
    const m = ready()
    if (!m) return
    addLayers(m)
    showPicture()
    showField()
    showPlacement()
    void showRisk()
    if (outline.value) zoomToField()
  })

  watch(() => risk.view, showRisk, { deep: true })
  watch([() => picture.value?.key, pictureShown, warm], showPicture)
  watch([placing, styleVersion], warmWhenIdle, { immediate: true })
  watch([outline, placing], showField)
  watch([() => outline.value?.field_id, wide, () => flow.section], () => {
    if (outline.value && flow.section !== 'maps') zoomToField()
  })
  watch([placing, () => field.preview, () => field.corners, () => field.point, () => field.drawing], showPlacement)
  watch(() => field.place, zoomToPlace)
  // "Start a new field" leaves the field: show all of Ireland again, not the old field
  watch(
    () => flow.fieldId,
    (id, previous) => {
      if (!id && previous && flow.section !== 'maps') {
        field.clearPlacement()
        zoomToIreland()
      }
    },
  )
}
