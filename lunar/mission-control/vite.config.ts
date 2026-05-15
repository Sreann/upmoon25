import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const bridgeProxy = {
  '/mission/ws': {
    target: 'http://127.0.0.1:8770',
    ws: true,
    changeOrigin: true,
  },
  '/healthz': {
    target: 'http://127.0.0.1:8770',
    changeOrigin: true,
  },
  '/camera': {
    target: 'http://127.0.0.1:8767',
    ws: true,
    changeOrigin: true,
  },
  '/sensor': {
    target: 'http://127.0.0.1:8767',
    ws: true,
    changeOrigin: true,
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    port: 5173,
    proxy: bridgeProxy,
  },
  preview: {
    host: true,
    port: 4173,
    proxy: bridgeProxy,
  },
})
