import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: Number(process.env.RLM_LENS_FRONTEND_PORT ?? 5173),
  },
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom'],
          trace: ['reactflow'],
          editor: ['@uiw/react-codemirror'],
          icons: ['lucide-react'],
        },
      },
    },
  },
});
