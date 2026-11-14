# GrowÉire · frontend

Landing page and app shell for GrowÉire: crop-rotation decision support built on NASA Earth observations, piloted in Ireland.

## Stack

Vue 3 + TypeScript · Vite · Tailwind CSS v4 · shadcn-vue (reka-ui) · vue-router

## Run

```bash
cd frontend
npm ci
npm run dev        # http://localhost:5173 (API calls go to http://localhost:8080)
npm run dev:mock   # same, but the API is answered from backend/tests/fixtures/api (no backend needed)
npm run build      # type-check + production build into dist/
npm run test       # unit tests (Vitest)
npm run gen:api    # regenerate src/lib/api-types.ts from ../backend/openapi.json
```

Add `?static=1` to any URL to freeze all motion in its final state (screenshots).

## Notes

- Routes: `/` landing page; `/app` field app (map + guided steps, step in `?s=1..4`), with `/app/maps`, `/app/words`, `/app/sources`.
- The field app has its own theme (`html.theme-app` in `src/style.css`, shadcn-vue preset `aJRWQJl`); the landing page keeps its own palette.
- How it works screenshot: set `HOW_IT_WORKS_SCREENSHOT` in `src/config/assets.ts` when the real interface exists (a placeholder is shown until then).
- Data-source logos and their licence status: `public/logos/SOURCES.md`. Get permission for the NASA, Met Éireann and Teagasc logos before public release.
- Hero photo: credit and licence still to be confirmed.
