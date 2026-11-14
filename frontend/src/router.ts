import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'

const SECTION = ':section(maps|words|sources)?'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    // The field app. One view serves the guided steps (`?s=2`) and the "More" pages, before a
    // field exists (`/app`) and after (`/app/field/f_1`), so the map is never rebuilt between them.
    {
      path: `/app/${SECTION}`,
      name: 'workspace',
      component: () => import('./views/WorkspaceView.vue'),
      meta: { app: true },
    },
    {
      path: `/app/field/:id/${SECTION}`,
      name: 'field',
      component: () => import('./views/WorkspaceView.vue'),
      meta: { app: true },
    },
    // One-page summary to print and bring to the advisor
    {
      path: '/app/field/:id/print',
      name: 'print',
      component: () => import('./views/PrintView.vue'),
      meta: { app: true },
    },
  ],
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    // Tapping an answer changes the URL but must not move the page
    if (to.meta.app && from.meta.app && to.path === from.path && to.query.s === from.query.s) return false
    return { top: 0 }
  },
})

// The field app has its own theme (see `html.theme-app` in style.css). The class goes on
// <html> so that menus and sheets rendered at the end of <body> are themed too.
router.beforeEach((to) => {
  document.documentElement.classList.toggle('theme-app', to.meta.app === true)
})
