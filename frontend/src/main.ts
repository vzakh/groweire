import { createApp } from 'vue'
import { createPinia } from 'pinia'
import '@fontsource/manrope/500.css'
import '@fontsource/manrope/600.css'
import '@fontsource/manrope/700.css'
import '@fontsource/atkinson-hyperlegible/400.css'
import '@fontsource/atkinson-hyperlegible/700.css'
import './style.css'
import App from './App.vue'
import { router } from './router'
import { initTextScale } from './composables/useTextScale'
import { wakeServer } from './lib/api'

// ?static=1 freezes all motion in its final state (screenshots / Figma capture)
if (new URLSearchParams(window.location.search).get('static') === '1') {
  document.documentElement.classList.add('is-static')
}
initTextScale()
// Free hosting sleeps when idle: start waking the API while the visitor reads the landing page
wakeServer()

/**
 * `npm run dev:mock` answers the API from recorded responses, so the app runs without a backend.
 * The mock code is a separate chunk that a normal build never loads.
 */
async function enableMocking() {
  if (import.meta.env.VITE_MOCK !== '1') return
  const { worker } = await import('./mocks/browser')
  await worker.start({ onUnhandledFrame: 'bypass' })
}

// Mount only once the mocks are listening, so the first request is never missed
void enableMocking().then(() => {
  createApp(App).use(createPinia()).use(router).mount('#app')
})
