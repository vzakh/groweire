import { describe, expect, it } from 'vitest'
import { copy } from '@/copy/en'
import { toFriendlyError } from './api'

describe('toFriendlyError', () => {
  it('sends a busy place search to the map', () => {
    const error = toFriendlyError({ detail: 'Busy', code: 'place_search_busy' }, 503)
    expect(error.code).toBe('place_search_busy')
    expect(error.next).toBe('Tap your field on the map instead.')
  })

  it('treats a missing field as an out-of-date link', () => {
    const error = toFriendlyError({ detail: 'We could not find that field.', code: 'field_not_found' }, 404)
    expect(error.message).toBe(copy.errors.field_not_found.message)
  })

  it('groups every "*_unavailable" code as a data source that is not answering', () => {
    for (const code of ['power_unavailable', 'climate_unavailable', 'risk_unavailable', 'db_unavailable']) {
      expect(toFriendlyError({ code }, 503).message).toBe(copy.errors.data_unavailable.message)
    }
  })

  it('falls back on the status when the body has no code', () => {
    expect(toFriendlyError({ detail: [] }, 422).message).toBe(copy.errors.invalid.message)
    expect(toFriendlyError(undefined, 500).code).toBe('unknown')
  })

  it('reads a network failure as being offline', () => {
    expect(toFriendlyError(new TypeError('Failed to fetch')).code).toBe('offline')
  })

  it('always says what to do next', () => {
    for (const entry of Object.values(copy.errors)) {
      expect(entry.next.length).toBeGreaterThan(0)
    }
  })
})
