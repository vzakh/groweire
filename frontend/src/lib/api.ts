import createClient, { type Middleware } from 'openapi-fetch'
import { copy, type ErrorKey } from '@/copy/en'
import type { components, paths } from './api-types'

/** Response and request shapes, generated from backend/openapi.json (`npm run gen:api`). */
export type Schemas = components['schemas']

/** The API contract this frontend was built against. */
export const EXPECTED_CONTRACT = '2.0'

function requestId(): string {
  // randomUUID needs a secure context; a phone on the local network over http does not have one.
  return globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2)
}

const withRequestId: Middleware = {
  onRequest({ request }) {
    request.headers.set('X-Request-ID', requestId())
    return request
  },
}

/** Typed client. Paths already include `/api/v1`, so the base is the page's own origin. */
export const api = createClient<paths>({ baseUrl: '' })
api.use(withRequestId)

export interface FriendlyError {
  /** The API's error code, or our own key when there is none. */
  code: string
  /** What happened, in plain words. */
  message: string
  /** What the person can do next. */
  next: string
}

const CODE_TO_KEY: Record<string, ErrorKey> = {
  place_search_busy: 'place_search_busy',
  nominatim_unavailable: 'place_search_busy',
  field_not_found: 'field_not_found',
  field_input_ambiguous: 'invalid',
  payload_too_large: 'too_large',
  dataset_not_loaded: 'data_unavailable',
}

function keyFor(code: string | undefined, status: number | undefined): ErrorKey {
  if (code && CODE_TO_KEY[code]) return CODE_TO_KEY[code]
  if (code?.endsWith('_unavailable')) return 'data_unavailable'
  if (status === 404) return 'field_not_found'
  if (status === 413) return 'too_large'
  if (status === 422) return 'invalid'
  if (status === 503) return 'data_unavailable'
  return 'unknown'
}

/**
 * Turn any failure into a sentence that says what happened and what to do next.
 * `error` is the API's `{detail, code}` body, or whatever `fetch` threw.
 */
export function toFriendlyError(error: unknown, status?: number): FriendlyError {
  // fetch rejects with a TypeError when the network is down or the server is unreachable
  if (error instanceof TypeError) {
    return { code: 'offline', ...copy.errors.offline }
  }
  const code =
    typeof error === 'object' && error !== null && typeof (error as { code?: unknown }).code === 'string'
      ? (error as { code: string }).code
      : undefined
  const key = keyFor(code, status)
  return { code: code ?? key, ...copy.errors[key] }
}

/** Warn in the console when the API speaks a different contract than this build expects. */
export async function checkContract(): Promise<void> {
  try {
    const { data } = await api.GET('/api/v1/health/ready')
    if (data && data.contract_version !== EXPECTED_CONTRACT) {
      console.warn(
        `API contract is ${data.contract_version}, this app was built for ${EXPECTED_CONTRACT}.`,
      )
    }
  } catch {
    // The API is unreachable. Each screen reports its own failed request, so stay quiet here.
  }
}
