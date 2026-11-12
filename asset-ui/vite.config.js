import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_FRAPPE_URL || 'http://127.0.0.1:8002'
  const site = env.VITE_FRAPPE_SITE || ''
  // Same-origin proxy: session cookie works without CORS
  const proxy = (extra = {}) => ({
    target,
    changeOrigin: false,
    headers: site ? { Host: site, 'X-Frappe-Site-Name': site } : {},
    ...extra,
  })
  return {
    plugins: [vue()],
    resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
    server: {
      port: 5173,
      proxy: {
        '/api': proxy(),
        '/files': proxy(),
        '/private': proxy(),
        '/socket.io': proxy({ ws: true }),
      },
    },
    build: { outDir: 'dist', emptyOutDir: true },
  }
})
