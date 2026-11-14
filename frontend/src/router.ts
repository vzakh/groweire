import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    // The field app: one view for the guided steps (`/app?s=2`) and the "More" pages
    // (`/app/maps`, `/app/words`, `/app/sources`), so the map is never rebuilt between them.
    {
      path: '/app/:section(maps|words|sources)?',
      name: 'workspace',
      component: () => import('./views/WorkspaceView.vue'),
    },
  ],
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    // Moving between steps of the app keeps the page where it is
    if (to.name === 'workspace' && from.name === 'workspace') return false
    return { top: 0 }
  },
})

// The field app has its own theme (see `html.theme-app` in style.css). The class goes on
// <html> so that menus and sheets rendered at the end of <body> are themed too.
router.beforeEach((to) => {
  document.documentElement.classList.toggle('theme-app', to.name === 'workspace')
})
