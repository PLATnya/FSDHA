import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  const host = env.VITE_DEV_HOST || env.HOST || '0.0.0.0'
  const portRaw = env.VITE_DEV_PORT || env.PORT
  const port = (() => {
    if (!portRaw) return 3000
    const n = Number(portRaw)
    return Number.isFinite(n) ? n : 3000
  })()
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      host,
      port,
      strictPort: true,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
