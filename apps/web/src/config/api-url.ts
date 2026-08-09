const configuredApiUrl = import.meta.env.PUBLIC_API_URL;

if (!configuredApiUrl) {
  throw new Error('Defina PUBLIC_API_URL no arquivo de configuração da Web.');
}

export const apiUrl = String(configuredApiUrl).replace(/\/+$/, '');
