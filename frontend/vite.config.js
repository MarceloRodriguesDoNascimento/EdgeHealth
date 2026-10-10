import { defineConfig } from 'vite';
export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: ['terminal.local'],
    proxy: { '/api': { target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:5000' } }
  },
  build: { outDir: 'dist', emptyOutDir: true }
});
