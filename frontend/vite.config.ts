import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  base: '/',
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    // Same-origin API in production; in development the API runs on :8080
    proxy: { '/api': 'http://localhost:8080' },
    // `npm run dev:mock` reads the recorded API responses in ../backend/tests/fixtures/api
    fs: { allow: ['..'] },
  },
  build: { outDir: 'dist' },
  // MapLibre starts its worker as an ES module
  worker: { format: 'es' },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
