(() => {
  const nativeFetch = window.fetch.bind(window);
  const configuredApiUrl = document.body?.dataset?.apiUrl || '/api/mail';
  let redirecting = false;

  function asUrl(input) {
    try {
      const raw = input instanceof Request ? input.url : String(input);
      return new URL(raw, window.location.origin);
    } catch {
      return null;
    }
  }

  function isMailApi(url) {
    if (!url) return false;
    try {
      const base = new URL(configuredApiUrl, window.location.origin);
      const basePath = base.pathname.replace(/\/+$/, '');
      return url.origin === base.origin && (url.pathname === basePath || url.pathname.startsWith(`${basePath}/`));
    } catch {
      return url.pathname === '/api/mail' || url.pathname.startsWith('/api/mail/');
    }
  }

  window.fetch = async function orbitalMailFetch(input, init = {}) {
    const url = asUrl(input);
    const response = await nativeFetch(input, isMailApi(url) ? { ...init, credentials: 'include' } : init);

    const controlAuthPath = /\/auth\/(?:start|callback|logout)$/.test(url?.pathname || '');
    if (response.status === 401 && isMailApi(url) && !controlAuthPath && !redirecting) {
      redirecting = true;
      const base = new URL(configuredApiUrl, window.location.origin);
      const startUrl = new URL(`${base.pathname.replace(/\/+$/, '')}/auth/start`, base.origin);
      startUrl.searchParams.set('return_to', `${window.location.pathname}${window.location.search}${window.location.hash}`);
      window.location.assign(startUrl.toString());
    }
    return response;
  };

  try {
    const base = new URL(configuredApiUrl, window.location.origin);
    const contextUrl = new URL(`${base.pathname.replace(/\/+$/, '')}/auth/context`, base.origin);
    window.fetch(contextUrl.toString(), { credentials: 'include', cache: 'no-store' }).catch(() => {});
  } catch {
    // A configuração inválida será exibida pelas chamadas normais da página.
  }

})();
