import { createApp } from 'vue'
import '@fontsource/manrope/500.css'
import '@fontsource/manrope/600.css'
import '@fontsource/manrope/700.css'
import '@fontsource/atkinson-hyperlegible/400.css'
import '@fontsource/atkinson-hyperlegible/700.css'
import './style.css'
import App from './App.vue'
import { router } from './router'

// ?static=1 freezes all motion in its final state (screenshots / Figma capture)
if (new URLSearchParams(window.location.search).get('static') === '1') {
  document.documentElement.classList.add('is-static')
}

createApp(App).use(router).mount('#app')
