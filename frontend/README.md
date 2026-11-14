# GrowÉire · frontend

Landing page and app shell for GrowÉire: crop-rotation decision support built on NASA Earth observations, piloted in Ireland.

## Stack

Vue 3 + TypeScript · Vite · Tailwind CSS v4 · shadcn-vue (reka-ui) · vue-router

## Run

```bash
cd frontend
npm ci
npm run dev        # http://localhost:5173
npm run build      # type-check + production build into dist/
```

Add `?static=1` to any URL to freeze all motion in its final state (screenshots).

## Notes

- Routes: `/` landing page, `/app` workspace (shell only for now).
- How it works screenshot: set `HOW_IT_WORKS_SCREENSHOT` in `src/config/assets.ts` when the real interface exists (a placeholder is shown until then).
- Data-source logos and their licence status: `public/logos/SOURCES.md`. Get permission for the NASA, Met Éireann and Teagasc logos before public release.
- Hero photo: credit and licence still to be confirmed.
