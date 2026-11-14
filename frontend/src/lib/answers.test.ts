import { describe, expect, it } from 'vitest'
import compareFixture from '../../../backend/tests/fixtures/api/rotations_compare.json'
import { buildCompareBody, riskCrop, rotationFromCrops, togglePriority } from './answers'
import { emptyAnswers, type Answers, type Priority } from './query'
import { shareLinks } from './share'

describe('togglePriority', () => {
  it('ranks by the order of taps', () => {
    let picked: Priority[] = []
    for (const id of ['simplicity', 'income_stability', 'soil_cover'] as const) {
      picked = togglePriority(picked, id).picked
    }
    expect(picked).toEqual(['simplicity', 'income_stability', 'soil_cover'])
  })

  it('refuses a fourth pick and says so', () => {
    const three: Priority[] = ['simplicity', 'income_stability', 'soil_cover']
    const result = togglePriority(three, 'water_use')
    expect(result.full).toBe(true)
    expect(result.picked).toEqual(three)
  })

  it('removes a picked card on a second tap, and the rest move up', () => {
    const result = togglePriority(['simplicity', 'income_stability', 'soil_cover'], 'simplicity')
    expect(result).toEqual({ picked: ['income_stability', 'soil_cover'], full: false })
  })
})

describe('rotationFromCrops', () => {
  it('needs last year', () => {
    expect(rotationFromCrops([null, 'winter_wheat', null, null])).toBeNull()
  })

  it('puts the oldest year first', () => {
    expect(rotationFromCrops(['spring_barley', 'winter_wheat', 'spring_oats', 'potatoes'])).toEqual([
      'potatoes',
      'spring_oats',
      'winter_wheat',
      'spring_barley',
    ])
  })

  it('fills a "not sure" year with the crop grown most often, never a new crop', () => {
    expect(rotationFromCrops(['spring_barley', null, null, null])).toEqual(Array(4).fill('spring_barley'))
    expect(rotationFromCrops(['spring_barley', 'winter_wheat', 'winter_wheat', null])).toEqual([
      'winter_wheat',
      'winter_wheat',
      'winter_wheat',
      'spring_barley',
    ])
  })
})

describe('buildCompareBody', () => {
  const answers: Answers = {
    ...emptyAnswers(),
    crops: ['spring_barley', 'spring_barley', 'spring_barley', 'spring_barley'],
    priorities: ['income_stability', 'simplicity', 'soil_cover'],
    livestock: false,
    contracts: ['malting_barley'],
    excluded: ['potatoes'],
  }

  it('builds exactly the request the API recorded its fixture with', () => {
    expect(buildCompareBody('f_00000001', answers)).toEqual(compareFixture._request.body)
  })

  it('sends "not asked" as null, so the API lists it as a gap instead of filtering on it', () => {
    const body = buildCompareBody('f_1', { ...emptyAnswers(), crops: ['spring_oats', null, null, null] })
    expect(body?.constraints).toMatchObject({ has_livestock: null, equipment: null, excluded_crops: [] })
    expect(body?.priorities).toEqual([])
  })

  it('waits for last year before comparing', () => {
    expect(buildCompareBody('f_1', emptyAnswers())).toBeNull()
  })
})

describe('riskCrop', () => {
  it('is the crop grown last year', () => {
    expect(riskCrop({ ...emptyAnswers(), crops: ['winter_wheat', 'spring_barley', null, null] })).toBe('winter_wheat')
    expect(riskCrop(emptyAnswers())).toBeNull()
  })
})

describe('shareLinks', () => {
  const url = 'https://example.org/app/field/f_1?c=-,spring_barley&s=4'
  const links = shareLinks('My field answer:', url, 'My field answer')

  it('makes WhatsApp, text and email links that carry the whole address', () => {
    for (const link of Object.values(links)) {
      expect(decodeURIComponent(link)).toContain(url)
    }
    expect(links.whatsapp).toMatch(/^https:\/\/wa\.me\/\?text=/)
    expect(links.sms).toMatch(/^sms:\?&body=/)
    expect(links.email).toMatch(/^mailto:\?subject=My%20field%20answer&body=/)
  })
})
