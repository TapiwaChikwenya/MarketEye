import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    host: true,
    // LAN IPs and localhost are allowed by default (see server.allowedHosts in Vite docs).
    // For Bonjour hostnames (e.g. my-mac.local), set:
    // __VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS=my-mac.local
  },
})
