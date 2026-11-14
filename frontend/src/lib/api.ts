import { ref, shallowRef } from 'vue'
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

/** A failed API call, already worded for the person using the app. */
export class ApiFailure extends Error {
  readonly friendly: FriendlyError
  readonly status?: number
  constructor(friendly: FriendlyError, status?: number) {
    super(friendly.message)
    this.friendly = friendly
    this.status = status
  }
}

/**
 * The data of an API call, or an `ApiFailure` that says what happened and what to do next.
 * The result is typed by the caller (a `Schemas[...]` shape): openapi-fetch widens fixed-length
 * arrays such as `[lon, lat]` to `number[]`, which would not match the generated schema types.
 */
export async function unwrap<T>(
  request: Promise<{ data?: unknown; error?: unknown; response: Response }>,
): Promise<T> {
  let result: { data?: unknown; error?: unknown; response: Response }
  try {
    result = await request
  } catch (thrown) {
    throw new ApiFailure(toFriendlyError(thrown))
  }
  if (result.error !== undefined || result.data === undefined) {
    throw new ApiFailure(toFriendlyError(result.error, result.response.status), result.response.status)
  }
  return result.data as T
}

/**
 * One piece of loaded data with its loading and error state. A newer `run` wins over an older
 * one that is still in flight, so a slow answer never overwrites a fresh one.
 */
export function useResource<T>() {
  const data = shallowRef<T | null>(null)
  const error = shallowRef<FriendlyError | null>(null)
  const loading = ref(false)
  let latest = 0

  async function run(load: () => Promise<T>): Promise<T | null> {
    const mine = ++latest
    loading.value = true
    error.value = null
    try {
      const value = await load()
      if (mine === latest) data.value = value
      return value
    } catch (thrown) {
      if (mine === latest) {
        error.value = thrown instanceof ApiFailure ? thrown.friendly : toFriendlyError(thrown)
      }
      return null
    } finally {
      if (mine === latest) loading.value = false
    }
  }

  function reset() {
    latest++
    data.value = null
    error.value = null
    loading.value = false
  }

  return { data, error, loading, run, reset }
}
