import { defineConfig } from 'astro/config';
import node from '@astrojs/node';
import {loadConfigEnv} from './scripts/load-env.mjs';

const fileEnv = loadConfigEnv();
const env = {...process.env, ...fileEnv};
const publicDefines = Object.fromEntries(
    Object.entries(env)
        .filter(([key]) => key.startsWith('PUBLIC_'))
        .map(([key, value]) => [`import.meta.env.${key}`, JSON.stringify(value)]),
);

export default defineConfig({
  output: 'server',
  adapter: node({ mode: 'standalone' }),
    base: '/orbital-mail',
    server: {
        host: env.APP_HOST || '0.0.0.0',
        port: Number(env.APP_PORT || 4106),
    },
    vite: {
        define: publicDefines,
        envPrefix: 'PUBLIC_',
    },
});
