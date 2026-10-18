import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Dev: API runs on :8077 (uvicorn athena.api:app --port 8077)
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    strictPort: true,
    proxy: { '/api': { target: 'http://localhost:8077', ws: true } }, // ws: live follow-along
  },
})
