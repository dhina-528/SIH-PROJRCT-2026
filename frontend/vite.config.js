import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',   // bind to all interfaces — fixes IPv4/IPv6 mismatch
    // Proxy API calls to the FastAPI backend so we don't hit CORS issues in dev
    proxy: {
      '/find-post-office': 'http://127.0.0.1:8000',
      '/parser-status':    'http://127.0.0.1:8000',
    },
  },
})
