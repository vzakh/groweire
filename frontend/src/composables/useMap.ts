import { ref, shallowRef } from 'vue'
import type { Map as MapLibreMap } from 'maplibre-gl'

/**
 * The app's one map. It is created once and lives in its own element, which the visible
 * <MapCanvas> adopts; switching step or layout moves the element and never rebuilds the map,
 * so zoom and position are kept. MapLibre is a separate chunk, loaded after the first paint.
 */
const BASEMAP = 'https://tiles.openfreemap.org/styles/liberty'
const FALLBACK_BASEMAP = 'https://demotiles.maplibre.org/style.json'
/** The island of Ireland, west / south / east / north. The map opens fitted to it on any screen. */
const IRELAND: [number, number, number, number] = [-10.7, 51.3, -5.3, 55.5]

type MapStatus = 'idle' | 'loading' | 'ready' | 'error'

const map = shallowRef<MapLibreMap | null>(null)
const status = ref<MapStatus>('idle')
let container: HTMLDivElement | null = null
let starting: Promise<void> | null = null

function getContainer(): HTMLDivElement {
  if (!container) {
    container = document.createElement('div')
    container.style.width = '100%'
    container.style.height = '100%'
  }
  return container
}

async function start(): Promise<void> {
  status.value = 'loading'
  try {
    const [{ Map, NavigationControl, setWorkerUrl }, { default: workerUrl }] = await Promise.all([
      import('maplibre-gl'),
      // MapLibre 6 looks for its worker file next to its own module, which a bundler moves.
      // Let Vite bundle the worker and tell MapLibre where it ended up.
      import('maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'),
      import('maplibre-gl/dist/maplibre-gl.css'),
    ])
    setWorkerUrl(workerUrl)
    const instance = new Map({
      container: getContainer(),
      style: BASEMAP,
      bounds: IRELAND,
      fitBoundsOptions: { padding: 24 },
      attributionControl: { compact: false },
    })
    instance.addControl(new NavigationControl({ showCompass: false }), 'top-right')

    let styleLoaded = false
    let triedFallback = false
    instance.on('style.load', () => {
      styleLoaded = true
      status.value = 'ready'
    })
    instance.on('error', () => {
      // Tile errors after the style has loaded are not fatal: the map stays usable.
      if (styleLoaded) return
      if (!triedFallback) {
        triedFallback = true
        instance.setStyle(FALLBACK_BASEMAP)
      } else {
        status.value = 'error'
      }
    })
    map.value = instance
  } catch {
    status.value = 'error'
  }
}

export function useMap() {
  /** Show the map inside `host`. The first call also starts loading it, after the first paint. */
  function attach(host: HTMLElement) {
    host.appendChild(getContainer())
    if (map.value) {
      map.value.resize()
    } else if (!starting) {
      starting = new Promise<void>((resolve) => {
        requestAnimationFrame(() => setTimeout(() => start().then(resolve), 0))
      })
    }
  }

  /** Take the map out of `host` without destroying it. */
  function detach(host: HTMLElement) {
    if (container?.parentElement === host) host.removeChild(container)
  }

  return { map, status, attach, detach }
}
