import { defineConfig } from 'astro/config';
import { loadEnv } from 'vite';
import node from '@astrojs/node';
import { fileURLToPath } from 'node:url';

const webRoot = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, webRoot, '');
  return {
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
  };
});
