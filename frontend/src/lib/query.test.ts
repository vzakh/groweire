import { describe, expect, it } from 'vitest'
import { answersToQuery, emptyAnswers, parseAnswers, parseMonth, parseStep, withStep, type Answers } from './query'

describe('parseStep', () => {
  it('reads steps 1 to 4', () => {
    expect(parseStep('1')).toBe(1)
    expect(parseStep('4')).toBe(4)
    expect(parseStep(['3', '2'])).toBe(3)
  })

  it('falls back to step 1 for anything else', () => {
    for (const value of [undefined, null, '', '0', '5', '2.5', 'abc', []]) {
      expect(parseStep(value)).toBe(1)
    }
  })
})

describe('withStep', () => {
  it('keeps the other answers in the URL', () => {
    expect(withStep({ c: 'spring_barley', s: '2' }, 3)).toEqual({ c: 'spring_barley', s: '3' })
  })

  it('drops `s` on step 1', () => {
    expect(withStep({ c: 'spring_barley', s: '2' }, 1)).toEqual({ c: 'spring_barley' })
  })

  it('round-trips through parseStep', () => {
    for (const step of [1, 2, 3, 4] as const) {
      expect(parseStep(withStep({}, step).s)).toBe(step)
    }
  })
})

describe('parseMonth', () => {
  it('reads the growing season, March to October', () => {
    expect(parseMonth('3')).toBe(3)
    expect(parseMonth('10')).toBe(10)
  })

  it('ignores months outside it', () => {
    for (const value of [undefined, '', '2', '11', 'july']) expect(parseMonth(value)).toBeNull()
  })
})

describe('answers in the URL', () => {
  const answers: Answers = {
    crops: ['spring_barley', 'winter_wheat', null, 'potatoes'],
    priorities: ['simplicity', 'income_stability'],
    livestock: true,
    contracts: ['malting_barley'],
    excluded: ['potatoes', 'maize_silage'],
  }

  it('writes crops oldest first, with `-` for a year the farmer was not sure about', () => {
    expect(answersToQuery(answers)).toEqual({
      c: 'potatoes,-,winter_wheat,spring_barley',
      p: 'simplicity,income_stability',
      k: 'ls1,ct.malting_barley,x.potatoes,x.maize_silage',
    })
  })

  it('round-trips', () => {
    expect(parseAnswers(answersToQuery(answers))).toEqual(answers)
    expect(parseAnswers(answersToQuery(emptyAnswers()))).toEqual(emptyAnswers())
  })

  it('writes nothing for no answers, and keeps "no livestock" apart from "not asked"', () => {
    expect(answersToQuery(emptyAnswers())).toEqual({})
    expect(answersToQuery({ ...emptyAnswers(), livestock: false })).toEqual({ k: 'ls0' })
  })

  it('reads only last year when one crop is given', () => {
    expect(parseAnswers({ c: 'spring_barley' }).crops).toEqual(['spring_barley', null, null, null])
  })

  it('drops anything it does not know, and never keeps more than three priorities', () => {
    const parsed = parseAnswers({
      c: 'Spring Barley!,spring_oats',
      p: 'simplicity,nonsense,simplicity,soil_cover,water_use,pest_break',
      k: 'ls9,ct.<script>,x.potatoes',
    })
    expect(parsed.crops).toEqual(['spring_oats', null, null, null])
    expect(parsed.priorities).toEqual(['simplicity', 'soil_cover', 'water_use'])
    expect(parsed.livestock).toBeNull()
    expect(parsed.contracts).toEqual([])
    expect(parsed.excluded).toEqual(['potatoes'])
  })
})
