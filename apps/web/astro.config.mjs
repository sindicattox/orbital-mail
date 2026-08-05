import { defineConfig } from 'astro/config';
import node from '@astrojs/node';

const host = process.env.APP_HOST;
const port = Number(process.env.APP_PORT);

if (!host || !Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error('APP_HOST e APP_PORT devem vir de apps/web/config/<contexto>/app.env.');
}

export default defineConfig({
  output: 'server',
  adapter: node({ mode: 'standalone' }),
  server: { host, port },
  vite: { envPrefix: 'PUBLIC_' },
});
