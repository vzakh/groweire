import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

/** Mock API for `npm run dev:mock`: answers `/api/v1/*` from the backend's recorded fixtures. */
export const worker = setupWorker(...handlers)
