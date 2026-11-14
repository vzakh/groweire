/** Small geometry helpers for placing a field. Coordinates are [longitude, latitude] in degrees. */
export type LngLat = [number, number]

export interface Polygon {
  type: 'Polygon'
  coordinates: LngLat[][]
}

const EARTH_RADIUS_M = 6_371_008.8
const M_PER_DEG_LAT = (Math.PI / 180) * EARTH_RADIUS_M

/** Radius in metres of a circle with this area in hectares. */
export function radiusForArea(areaHa: number): number {
  return Math.sqrt((areaHa * 10_000) / Math.PI)
}

/** A circle of the given area around a point: the preview of an approximate field. */
export function circlePolygon(center: LngLat, areaHa: number, steps = 64): Polygon {
  const [lon, lat] = center
  const radius = radiusForArea(areaHa)
  const dLat = radius / M_PER_DEG_LAT
  const dLon = radius / (M_PER_DEG_LAT * Math.cos((lat * Math.PI) / 180))
  const ring: LngLat[] = []
  for (let i = 0; i < steps; i++) {
    const angle = (i / steps) * 2 * Math.PI
    ring.push([lon + dLon * Math.cos(angle), lat + dLat * Math.sin(angle)])
  }
  ring.push(ring[0]!)
  return { type: 'Polygon', coordinates: [ring] }
}

/** A closed polygon from the corners someone tapped. */
export function polygonFromCorners(corners: LngLat[]): Polygon {
  return { type: 'Polygon', coordinates: [[...corners, corners[0]!]] }
}

/** Area in hectares of a ring of corners (closed or not). Good to well under 1% at field size. */
export function areaHa(corners: LngLat[]): number {
  if (corners.length < 3) return 0
  const lat0 = corners.reduce((sum, c) => sum + c[1], 0) / corners.length
  const kx = M_PER_DEG_LAT * Math.cos((lat0 * Math.PI) / 180)
  let twice = 0
  for (let i = 0; i < corners.length; i++) {
    const [x1, y1] = corners[i]!
    const [x2, y2] = corners[(i + 1) % corners.length]!
    twice += x1 * kx * (y2 * M_PER_DEG_LAT) - x2 * kx * (y1 * M_PER_DEG_LAT)
  }
  return Math.abs(twice) / 2 / 10_000
}

/** [west, south, east, north] of any GeoJSON-style coordinate nest. */
export function bboxOf(coordinates: unknown): [number, number, number, number] | null {
  let west = Infinity
  let south = Infinity
  let east = -Infinity
  let north = -Infinity
  const visit = (node: unknown) => {
    if (!Array.isArray(node)) return
    if (typeof node[0] === 'number' && typeof node[1] === 'number') {
      west = Math.min(west, node[0])
      east = Math.max(east, node[0])
      south = Math.min(south, node[1])
      north = Math.max(north, node[1])
    } else {
      node.forEach(visit)
    }
  }
  visit(coordinates)
  return Number.isFinite(west) ? [west, south, east, north] : null
}
