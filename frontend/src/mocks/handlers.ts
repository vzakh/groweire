import { http, HttpResponse } from 'msw'

/**
 * Mock handlers built from the backend's recorded responses
 * (`backend/tests/fixtures/api/*.json`, real data, API contract 2.0).
 * Each fixture carries its own `_request {method, path, body, status}`; the handlers below
 * pick the fixture whose request is closest to the one the app made.
 */
interface Fixture {
  _fixture_source: string
  _request: { method: string; path: string; body: unknown; status: number }
  [key: string]: unknown
}

const files = import.meta.glob<Fixture>('../../../backend/tests/fixtures/api/*.json', {
  eager: true,
  import: 'default',
})

const fixtures: Record<string, Fixture> = {}
for (const [path, fixture] of Object.entries(files)) {
  fixtures[path.split('/').pop()!.replace('.json', '')] = fixture
}

/** The fixture's response: the recorded body without our bookkeeping keys, and its status. */
function reply(name: string) {
  const fixture = fixtures[name]
  if (!fixture) {
    return HttpResponse.json({ detail: `No fixture named ${name}`, code: 'mock_fixture_missing' }, { status: 500 })
  }
  const { _fixture_source, _request, _truncated_from, ...body } = fixture
  return HttpResponse.json(body, { status: _request.status })
}

const API = '/api/v1'

/**
 * Live place search for mock mode, with the same request and result shape as the backend
 * (backend/app/clients/nominatim.py): island of Ireland only, up to 5 places. Nominatim's usage
 * policy allows this from a browser at this volume (one search per button press, no autocomplete).
 * Any failure gives no results, and the app then says "tap the map instead".
 */
interface NominatimItem {
  display_name: string
  lat: string
  lon: string
  boundingbox?: string[]
  name?: string
  type?: string
  addresstype?: string
  address?: Record<string, string>
}

async function nominatim(q: string) {
  const params = new URLSearchParams({
    q,
    format: 'jsonv2',
    countrycodes: 'ie,gb',
    viewbox: '-10.7,55.5,-5.4,51.3',
    bounded: '1',
    limit: '10',
    addressdetails: '1',
  })
  try {
    const response = await fetch(`https://nominatim.openstreetmap.org/search?${params}`)
    if (!response.ok) return []
    const items = (await response.json()) as NominatimItem[]
    // Same tidying as the backend: island of Ireland only (of the UK, Northern Ireland), one per name
    const seen = new Set<string>()
    return items
      .filter((item) => item.address?.country_code !== 'gb' || item.address?.state === 'Northern Ireland')
      .map((item) => {
      const name = item.name || item.display_name.split(',')[0]!.trim()
      const county = item.address?.county ?? item.address?.state_district
      const box = item.boundingbox?.map(Number)
      return {
        name: county && county !== name ? `${name}, ${county}` : name,
        lon: Math.round(Number(item.lon) * 1e5) / 1e5,
        lat: Math.round(Number(item.lat) * 1e5) / 1e5,
        kind: item.addresstype || item.type || 'place',
        // Nominatim: south, north, west, east -> ours: west, south, east, north
        bbox: box && box.length === 4 ? [box[2], box[0], box[3], box[1]] : null,
      }
    })
      .filter((place) => !seen.has(place.name) && Boolean(seen.add(place.name)))
      .slice(0, 5)
  } catch {
    return []
  }
}
const PILOT_FIELDS = ['f_00000001', 'f_00000002']
const NON_PILOT_FIELD = 'f_00000003'

export const handlers = [
  http.get(`${API}/health/ready`, () => reply('health_ready')),

  http.get(`${API}/places`, async ({ request }) => {
    const q = (new URL(request.url).searchParams.get('q') ?? '').trim().toLowerCase()
    if (q === 'bagenalstwn') return reply('places_fallback')
    if (q.includes('bagenal')) return reply('places')
    // Any other search: ask OpenStreetMap live, like the backend (clients/nominatim.py)
    const { attribution, source } = fixtures.places ?? {}
    return HttpResponse.json({ results: await nominatim(q), attribution, source })
  }),

  http.post(`${API}/fields`, async ({ request }) => {
    const body = (await request.json()) as { point?: unknown; area_ha?: unknown; geometry?: unknown }
    const hasPoint = body.point != null && body.area_ha != null
    const hasShape = body.geometry != null
    if (hasPoint === hasShape) return reply('error_validation')
    return reply(hasShape ? 'fields_create_polygon' : 'fields_create_point')
  }),

  http.get(`${API}/fields/:id/conditions`, ({ params }) => {
    if (params.id === NON_PILOT_FIELD) return reply('conditions_non_pilot')
    if (PILOT_FIELDS.includes(String(params.id))) return reply('conditions_pilot')
    return reply('error_field_not_found')
  }),

  // There is no recorded field for the non-pilot id yet, so only the pilot field restores.
  http.get(`${API}/fields/:id`, ({ params }) =>
    reply(params.id === 'f_00000001' ? 'fields_get' : 'error_field_not_found'),
  ),

  http.post(`${API}/predict/stress-risk`, async ({ request }) => {
    const body = (await request.json()) as { field_id?: string; crop_id?: string | null }
    if (body.field_id === NON_PILOT_FIELD) return reply('predict_non_pilot')
    return reply(body.crop_id ? 'predict_seasonal_profile' : 'predict_seasonal_profile_no_crop')
  }),

  http.get(`${API}/crops`, () => reply('crops')),

  http.post(`${API}/rotations/compare`, () => reply('rotations_compare')),

  // The recorded maps are for July; every month answers with them until more are recorded.
  http.get(`${API}/layers/stress-risk`, ({ request }) => {
    const type = new URL(request.url).searchParams.get('type')
    return reply(type === 'drought' ? 'layers_stress_risk_drought' : 'layers_stress_risk')
  }),

  http.get(`${API}/layers`, () => reply('layers')),

  http.get(`${API}/glossary`, () => reply('glossary')),
]
