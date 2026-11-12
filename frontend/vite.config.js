import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

const apiProxy = {
  target: 'http://127.0.0.1:8000',
  changeOrigin: true,
  rewrite: (path) => path.replace(/^\/api/, ''),
}

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
  ],
  // Écoute sur toutes les interfaces : l'application est joignable depuis les autres
  // machines du réseau local (http://<ip-de-ce-poste>:5173).
  // /api est relayé vers l'API locale (VITE_API_URL=/api) : les autres machines ne joignent que
  // le port du frontend. L'API tourne dans WSL et n'est fiable qu'en localhost sur ce poste.
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: { '/api': apiProxy },
  },
  preview: {
    host: true,
    port: 4173,
    proxy: { '/api': apiProxy },
  },
})
