import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Create React App (react-scripts) is deprecated and pulled in ~60 vulnerable
// build-tool packages. Vite builds the same app with a fraction of them.
export default defineConfig({
  plugins: [react()],
  server: { port: 3000, host: '127.0.0.1' },
  preview: { port: 3000 },
  build: { outDir: 'dist', sourcemap: false, chunkSizeWarningLimit: 1200 },
});
