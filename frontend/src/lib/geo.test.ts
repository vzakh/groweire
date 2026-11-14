import { describe, expect, it } from 'vitest'
import { areaHa, bboxOf, circlePolygon, polygonFromCorners, radiusForArea, type LngLat } from './geo'

describe('radiusForArea', () => {
  it('gives about 178.4 m for a 10 ha field', () => {
    expect(radiusForArea(10)).toBeCloseTo(178.4, 1)
  })
})

describe('circlePolygon', () => {
  const center: LngLat = [-6.955, 52.705]

  it('is a closed ring around the point', () => {
    const ring = circlePolygon(center, 10).coordinates[0]!
    expect(ring).toHaveLength(65)
    expect(ring[0]).toEqual(ring[ring.length - 1])
  })

  it('covers the area that was asked for', () => {
    for (const size of [0.5, 10, 40, 2000]) {
      const ring = circlePolygon(center, size).coordinates[0]!
      // A 64-sided shape is a touch smaller than the true circle
      expect(areaHa(ring.slice(0, -1)) / size).toBeGreaterThan(0.99)
      expect(areaHa(ring.slice(0, -1)) / size).toBeLessThan(1.001)
    }
  })
})

describe('areaHa', () => {
  it('is zero until there are three corners', () => {
    expect(areaHa([])).toBe(0)
    expect(areaHa([[-7, 52], [-7.01, 52]])).toBe(0)
  })

  it('measures a drawn field', () => {
    // About 680 m by 1,112 m at this latitude
    const corners: LngLat[] = [[-7.25, 52.65], [-7.24, 52.65], [-7.24, 52.66], [-7.25, 52.66]]
    expect(areaHa(corners)).toBeGreaterThan(70)
    expect(areaHa(corners)).toBeLessThan(80)
    expect(polygonFromCorners(corners).coordinates[0]).toHaveLength(5)
  })
})

describe('bboxOf', () => {
  it('finds the box of a polygon', () => {
    expect(bboxOf(circlePolygon([-7, 52], 10).coordinates)).toEqual([
      expect.closeTo(-7.0026, 3),
      expect.closeTo(51.9984, 3),
      expect.closeTo(-6.9974, 3),
      expect.closeTo(52.0016, 3),
    ])
  })

  it('returns null when there is nothing to measure', () => {
    expect(bboxOf([])).toBeNull()
    expect(bboxOf(undefined)).toBeNull()
  })
})
