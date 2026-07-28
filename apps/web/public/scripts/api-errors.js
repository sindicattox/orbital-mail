((global) => {
  if (global.OrbitalApiErrors) return;

  function detailText(detail) {
    if (typeof detail === 'string') return detail.trim();
    if (Array.isArray(detail)) return detailText(detail[0]);
    if (!detail || typeof detail !== 'object') return '';
    return detailText(detail.message || detail.msg || detail.detail);
  }

  function statusText(status) {
    if (status === 400) return 'A solicitação enviada é inválida.';
    if (status === 401) return 'Sua sessão expirou. Entre novamente.';
    if (status === 403) return 'Você não tem permissão para executar esta ação.';
    if (status === 404) return 'O registro solicitado não foi encontrado.';
    if (status === 409) return 'A operação não pôde ser concluída no estado atual.';
    if (status === 413) return 'O arquivo enviado excede o tamanho permitido.';
    if (status === 415) return 'O formato do arquivo não é permitido.';
    if (status === 422) return 'Revise os dados informados.';
    if (status >= 500) return 'O serviço encontrou um erro. Tente novamente em instantes.';
    return '';
  }

  function fromPayload(payload, status, fallback) {
    return detailText(payload?.detail ?? payload?.message ?? payload) || statusText(status) || fallback;
  }

  async function fromResponse(response, fallback) {
    const payload = await response.json().catch(() => null);
    return fromPayload(payload, response.status, fallback);
  }

  function fromException(error, fallback) {
    if (error?.name === 'AbortError') return 'A operação excedeu o tempo limite. Tente novamente.';
    const message = error instanceof Error ? error.message.trim() : '';
    if (/failed to fetch|networkerror|load failed/i.test(message)) {
      return 'Não foi possível conectar à API do Orbital Mail. Verifique se o serviço está disponível.';
    }
    if (error instanceof TypeError) return fallback;
    return message || fallback;
  }

  global.OrbitalApiErrors = Object.freeze({ fromException, fromPayload, fromResponse });
})(window);
