import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dev server proxies /api to the existing FastAPI backend, so the
// frontend never needs to hard-code a backend origin or deal with CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    allowedHosts: ['app.outzaar.com'],
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})