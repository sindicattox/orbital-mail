const configuredApiUrl = import.meta.env.PROD
  ? import.meta.env.PUBLIC_REMOTE_API_URL
  : import.meta.env.PUBLIC_LOCAL_API_URL;

if (!configuredApiUrl) {
  const variable = import.meta.env.PROD ? 'PUBLIC_REMOTE_API_URL' : 'PUBLIC_LOCAL_API_URL';
  throw new Error(`Defina ${variable} em apps/web/.env.`);
}

export const apiUrl = String(configuredApiUrl).replace(/\/+$/, '');
