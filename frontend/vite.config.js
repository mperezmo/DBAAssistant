import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Frontend Vite + React (Sprint 3)
export default defineConfig({
  plugins: [react()],
  server: { port: 3000, host: true },
  preview: { port: 3000, host: true },
});
