(() => {
  const SESSION_KEY = 'orbitalSession';
  const nativeFetch = window.fetch.bind(window);
  const configuredApiUrl = document.body?.dataset?.apiUrl || '/api/mail';
  const orbitalHomeUrl = document.body?.dataset?.orbitalHomeUrl || '/';
  let redirecting = false;

  function readSession() {
    try {
      return JSON.parse(window.localStorage.getItem(SESSION_KEY) || 'null');
    } catch {
      window.localStorage.removeItem(SESSION_KEY);
      return null;
    }
  }

  function accessToken() {
    const session = readSession();
    return session?.access_token || session?.token || '';
  }

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
    const base = new URL(configuredApiUrl, window.location.origin);
    const basePath = base.pathname.replace(/\/+$/, '');
    return url.origin === base.origin && (url.pathname === basePath || url.pathname.startsWith(`${basePath}/`));
  }

  function loginUrl() {
    const home = new URL(orbitalHomeUrl, window.location.origin);
    const login = new URL('/login', home.origin);
      login.searchParams.set('return_to', `${window.location.pathname}${window.location.search}${window.location.hash}`);
    return login.toString();
  }

  function goToLogin() {
    if (redirecting) return;
    redirecting = true;
    window.location.replace(loginUrl());
  }

  window.fetch = async function orbitalMailFetch(input, init = {}) {
    const url = asUrl(input);
    if (!isMailApi(url)) return nativeFetch(input, init);

    const token = accessToken();
    if (!token) {
      goToLogin();
      return new Response(JSON.stringify({ detail: 'Sessão não informada.' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const headers = new Headers(input instanceof Request ? input.headers : undefined);
    new Headers(init.headers || {}).forEach((value, key) => headers.set(key, value));
    headers.set('Authorization', `Bearer ${token}`);

    const response = await nativeFetch(input, { ...init, headers, credentials: 'include' });
    if (response.status === 401) {
      window.localStorage.removeItem(SESSION_KEY);
      goToLogin();
    }
    return response;
  };

  const token = accessToken();
  if (!token) {
    goToLogin();
    return;
  }

  const base = new URL(configuredApiUrl, window.location.origin);
  const contextUrl = new URL(`${base.pathname.replace(/\/+$/, '')}/auth/context`, base.origin);
  window.fetch(contextUrl.toString(), { cache: 'no-store' }).catch(() => {});
})();
