import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
      manifest: {
        name: 'Production RAG Chatbot',
        short_name: 'RAG Chat',
        description: 'Chat with your PDFs — citations, translations, study tools, and more.',
        theme_color: '#7e14ff',
        background_color: '#0f172a',
        display: 'standalone',
        start_url: '/dashboard',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'pwa-maskable-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Only precache the app shell (HTML/JS/CSS/icons). API calls
        // (chat, documents, auth) are intentionally NOT cached -- this is
        // a live RAG app, not a content site; stale cached answers or
        // stale auth state would be actively wrong, not just outdated.
        globPatterns: ['**/*.{js,css,html,svg,png,ico}'],
        navigateFallbackDenylist: [/^\/(auth|chat|documents|scan|study|compare|mindmap|agent|health|metrics)\//],
      },
    }),
  ],
  server: {
    // Mirrors nginx.conf's /api/ -> backend proxy in production, so the
    // frontend code can call `${API_BASE_URL}/...` identically in dev and
    // prod. Set VITE_API_BASE_URL=/api in frontend/.env for local dev too
    // (see .env.example), or leave it unset to keep hitting :8000 directly.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
