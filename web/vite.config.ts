import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss()
  ],
  server: {
    port: 3000,
    proxy: {
      '/recommend': { target: 'http://localhost:8000' },
      '/places': { target: 'http://localhost:8000' },
      '/route': { target: 'http://localhost:8000' },
      '/ai': { target: 'http://localhost:8000' },
      '/auth': { target: 'http://localhost:8000' },
      '/itineraries': { target: 'http://localhost:8000' },
      '/memories': { 
        target: 'http://localhost:8000',
        bypass: (req) => req.headers.accept?.includes('text/html') ? '/index.html' : undefined
      },
      '/trail-watch': { 
        target: 'http://localhost:8000',
        bypass: (req) => req.headers.accept?.includes('text/html') ? '/index.html' : undefined
      },
      '/telemetry': { target: 'http://localhost:8000' },
      '/uploads': { target: 'http://localhost:8000' },
      '/static': { target: 'http://localhost:8000' },
      '/health': { target: 'http://localhost:8000' },
    }
  }
})
