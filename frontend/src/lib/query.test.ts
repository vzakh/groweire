import { describe, expect, it } from 'vitest'
import { parseStep, withStep } from './query'

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
