import { defineConfig } from 'astro/config';
import node from '@astrojs/node';
import { fileURLToPath } from 'node:url';
import { loadEnv } from 'vite';

const webRoot = fileURLToPath(new URL('.', import.meta.url));
const fileEnv = loadEnv(process.env.NODE_ENV || 'development', webRoot, '');
const env = { ...fileEnv, ...process.env };

export default defineConfig({
  output: 'server',
  adapter: node({ mode: 'standalone' }),
  server: {
    host: env.APP_HOST || '0.0.0.0',
    port: Number(env.APP_PORT || 4104),
  },
  vite: {
    envDir: webRoot,
    envPrefix: 'PUBLIC_',
  },
});
