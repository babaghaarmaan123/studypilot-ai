import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    // Same-origin API calls in development, so no CORS surprises and the
    // production build can use a relative VITE_API_URL if you host together.
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/uploads': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    // Vercel serves these behind a CDN with long-lived caching, so splitting
    // the heavy, rarely-changing libraries into their own files means an app
    // code change does not invalidate them.
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          charts: ['chart.js', 'react-chartjs-2'],
          motion: ['framer-motion'],
          // Only used by the timetable export on the Settings page.
          pdf: ['jspdf', 'jspdf-autotable'],
          calendar: ['react-calendar'],
        },
      },
    },
    chunkSizeWarningLimit: 700,
  },
})
