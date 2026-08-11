import '../scripts/api-errors.js';
import { mailStyles } from './mail/styles.js';
import { escapeHtml, formatDate, joinUrl } from './mail/shared.js';

const TAG_NAME = 'orbital-mail';
const apiErrors = window.OrbitalApiErrors;

class OrbitalMail extends HTMLElement {
  static observedAttributes = ['api-base', 'base-url', 'theme'];

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.selectedCampaignId = null;
    this.redirecting = false;
    this.isDev = window.orbitalMailAuthContext?.is_dev === true;
    this.authContextHandler = (event) => {
      this.isDev = event.detail?.is_dev === true;
      if (this.isDev) this.loadRecipientFilters();
      this.loadCampaigns();
    };
  }

  connectedCallback() {
    this.render();
    this.bindEvents();
    this.showSavedMessage();
    document.addEventListener('orbital-mail-auth-context', this.authContextHandler);
    if (this.isDev) this.loadRecipientFilters();
    this.loadCampaigns();
  }

  disconnectedCallback() {
    document.removeEventListener('orbital-mail-auth-context', this.authContextHandler);
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (!this.isConnected || oldValue === newValue || name === 'theme') return;
    if (this.isDev) this.loadRecipientFilters();
    this.loadCampaigns();
  }

  get apiBase() {
    return (this.getAttribute('api-base') || '/api/mail').replace(/\/+$/, '');
  }

  get baseUrl() {
    return (this.getAttribute('base-url') || '').replace(/\/+$/, '');
  }

  moduleUrl(path) {
    return joinUrl(this.baseUrl, path);
  }

  apiUrl(path) {
    return new URL(joinUrl(this.apiBase, path), window.location.origin);
  }

  async request(path, init = {}) {
    const response = await fetch(this.apiUrl(path), { ...init, credentials: 'include' });
    if (response.status === 401) this.startAuthentication();
    return response;
  }

  startAuthentication() {
    if (this.redirecting) return;
    this.redirecting = true;
    const orbitalHome = document.body?.dataset?.orbitalHomeUrl || '/';
    const loginUrl = new URL('/login', new URL(orbitalHome, window.location.origin).origin);
    loginUrl.searchParams.set('return_to', `${window.location.pathname}${window.location.search}${window.location.hash}`);
    window.location.replace(loginUrl.toString());
  }

  emitError(message) {
    this.dispatchEvent(new CustomEvent('orbital-module-error', {
      bubbles: true,
      composed: true,
      detail: { message },
    }));
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>${mailStyles}</style>
      <section class="page-head">
        <div><h1>Campanhas</h1><p>Cadastre e mantenha as campanhas salvas no Oracle.</p></div>
        <a class="button" data-new-campaign>Nova campanha</a>
      </section>

      <div data-message class="message" hidden></div>
      <dialog data-queue-dialog class="queue-dialog dev-highlight">
        <form method="dialog" class="queue-card">
          <div class="queue-head">
            <div><h2>Preparar destinatários</h2><p data-queue-campaign-name>Campanha</p></div>
            <button class="icon-button" value="cancel" aria-label="Fechar">Fechar</button>
          </div>
          <div class="form-grid">
            <label>Situação associativa
              <select data-queue-associative><option value="">Todas</option></select>
            </label>
            <label>Situação funcional
              <select data-queue-functional><option value="">Todas</option></select>
            </label>
            <label>Perfil
              <select data-queue-profile><option value="">Todos</option></select>
            </label>
            <label>E-mail de teste
              <input data-queue-test-email type="email" placeholder="Opcional: todos os envios irão para este e-mail">
              <small>Quando informado, substitui o e-mail real sem alterar a quantidade de destinatários.</small>
            </label>
          </div>
          <div data-queue-progress-box class="queue-progress-box" hidden>
            <div class="queue-progress-row"><strong data-queue-progress-text>0 de 0</strong><span data-queue-progress-percent>0%</span></div>
            <progress data-queue-progress value="0" max="100"></progress>
            <p data-queue-progress-detail>Preparando fila...</p>
          </div>
          <div data-queue-summary class="queue-summary" hidden></div>
          <div data-queue-error class="message error" hidden></div>
          <div class="queue-actions">
            <button data-clear-queue class="button secondary danger" type="button" hidden>Limpar fila</button>
            <button class="button secondary" value="cancel">Cancelar</button>
            <button data-prepare-queue class="button" type="button">Preparar fila</button>
          </div>
        </form>
      </dialog>

      <div class="table-wrap">
        <table>
          <thead data-campaign-head></thead>
          <tbody data-campaign-rows></tbody>
        </table>
      </div>
    `;

    this.head = this.shadowRoot.querySelector('[data-campaign-head]');
    this.rows = this.shadowRoot.querySelector('[data-campaign-rows]');
    this.message = this.shadowRoot.querySelector('[data-message]');
    this.queueDialog = this.shadowRoot.querySelector('[data-queue-dialog]');
    this.queueAssociative = this.shadowRoot.querySelector('[data-queue-associative]');
    this.queueFunctional = this.shadowRoot.querySelector('[data-queue-functional]');
    this.queueProfile = this.shadowRoot.querySelector('[data-queue-profile]');
    this.queueTestEmail = this.shadowRoot.querySelector('[data-queue-test-email]');
    this.prepareQueueButton = this.shadowRoot.querySelector('[data-prepare-queue]');
    this.clearQueueButton = this.shadowRoot.querySelector('[data-clear-queue]');
    this.queueProgressBox = this.shadowRoot.querySelector('[data-queue-progress-box]');
    this.queueProgress = this.shadowRoot.querySelector('[data-queue-progress]');
    this.queueProgressText = this.shadowRoot.querySelector('[data-queue-progress-text]');
    this.queueProgressPercent = this.shadowRoot.querySelector('[data-queue-progress-percent]');
    this.queueProgressDetail = this.shadowRoot.querySelector('[data-queue-progress-detail]');
    this.queueSummary = this.shadowRoot.querySelector('[data-queue-summary]');
    this.queueError = this.shadowRoot.querySelector('[data-queue-error]');
    this.shadowRoot.querySelector('[data-new-campaign]').href = this.moduleUrl('/campanhas/nova');
  }

  bindEvents() {
    this.rows.addEventListener('click', (event) => this.handleRowAction(event));
    this.prepareQueueButton.addEventListener('click', () => this.prepareQueue());
    this.clearQueueButton.addEventListener('click', () => this.clearQueue());
  }

  showMessage(text, type = 'error') {
    this.message.hidden = false;
    this.message.className = `message ${type}`;
    this.message.textContent = text;
    if (type === 'error') this.emitError(text);
  }

  setQueueError(text = '') {
    this.queueError.hidden = !text;
    this.queueError.textContent = text;
    if (text) this.emitError(text);
  }

  showSavedMessage() {
    if (!this.hasAttribute('standalone')) return;
    const saved = new URLSearchParams(window.location.search).get('saved');
    if (!saved) return;
    this.showMessage(saved === 'updated' ? 'Campanha alterada com sucesso.' : 'Campanha cadastrada com sucesso.', 'success');
    history.replaceState({}, '', this.moduleUrl('/campanhas'));
  }

  async loadCampaigns() {
    const columns = this.isDev ? 6 : 4;
    this.head.innerHTML = this.isDev
      ? '<tr><th>Ações</th><th>Nome interno</th><th>Assunto</th><th>Remetente</th><th>Status</th><th>Atualização</th></tr>'
      : '<tr><th>Ações</th><th>Assunto</th><th>Status</th><th>Atualização</th></tr>';
    this.rows.innerHTML = `<tr><td colspan="${columns}" class="empty">Carregando campanhas...</td></tr>`;
    try {
      const response = await this.request('/campaigns');
      if (!response.ok) throw new Error(await apiErrors.fromResponse(response, 'Não foi possível carregar as campanhas.'));
      const campaigns = await response.json();
      if (!campaigns.length) {
        this.rows.innerHTML = `<tr><td colspan="${columns}" class="empty">Nenhuma campanha cadastrada.</td></tr>`;
        return;
      }
      this.rows.innerHTML = campaigns.map((campaign) => {
        const actions = `
          <a class="icon-button" href="${this.moduleUrl(`/campanhas/${campaign.id}`)}" title="Editar">Editar</a>
          ${this.isDev ? `<a class="icon-button dev-action" href="${this.moduleUrl(`/campanhas/${campaign.id}/destinatarios`)}">Ver fila</a>
          <button class="icon-button dev-action" data-queue-id="${campaign.id}" data-name="${escapeHtml(campaign.internal_name)}" type="button">Preparar</button>` : ''}
          <button class="icon-button danger" data-delete-id="${campaign.id}" data-name="${escapeHtml(campaign.internal_name)}" type="button">Remover</button>`;
        return this.isDev ? `
          <tr>
            <td class="actions">${actions}</td>
            <td><strong>${escapeHtml(campaign.internal_name)}</strong></td>
            <td>${escapeHtml(campaign.subject)}</td>
            <td>${escapeHtml(campaign.sender_name || '')}<small>${escapeHtml(campaign.sender_email || '')}</small></td>
            <td><span class="badge">${escapeHtml(campaign.status)}</span></td>
            <td>${formatDate(campaign.updated_at || campaign.created_at)}</td>
          </tr>` : `
          <tr>
            <td class="actions">${actions}</td>
            <td>${escapeHtml(campaign.subject)}</td>
            <td><span class="badge">${escapeHtml(campaign.status)}</span></td>
            <td>${formatDate(campaign.updated_at || campaign.created_at)}</td>
          </tr>`;
      }).join('');
    } catch (error) {
      this.rows.innerHTML = `<tr><td colspan="${columns}" class="empty">Não foi possível carregar as campanhas.</td></tr>`;
      this.showMessage(apiErrors.fromException(error, 'Não foi possível carregar as campanhas.'));
    }
  }

  async handleRowAction(event) {
    const deleteButton = event.target.closest('[data-delete-id]');
    if (deleteButton) {
      await this.deleteCampaign(deleteButton);
      return;
    }

    const queueButton = event.target.closest('[data-queue-id]');
    if (queueButton) await this.openQueue(queueButton);
  }

  async deleteCampaign(button) {
    if (!window.confirm(`Remover a campanha "${button.dataset.name}"?`)) return;
    button.disabled = true;
    try {
      const response = await this.request(`/campaigns/${button.dataset.deleteId}`, { method: 'DELETE' });
      if (!response.ok) {
        throw new Error(await apiErrors.fromResponse(response, 'Não foi possível remover a campanha.'));
      }
      this.showMessage('Campanha removida com sucesso.', 'success');
      await this.loadCampaigns();
    } catch (error) {
      this.showMessage(apiErrors.fromException(error, 'Não foi possível remover a campanha.'));
      button.disabled = false;
    }
  }

  async openQueue(button) {
    this.selectedCampaignId = button.dataset.queueId;
    this.shadowRoot.querySelector('[data-queue-campaign-name]').textContent = button.dataset.name;
    this.setQueueError();
    this.queueProgressBox.hidden = true;
    this.queueSummary.hidden = true;
    this.queueAssociative.disabled = false;
    this.queueFunctional.disabled = false;
    this.queueProfile.disabled = false;
    this.queueTestEmail.disabled = false;
    this.prepareQueueButton.disabled = false;
    this.clearQueueButton.hidden = true;
    this.queueDialog.showModal();
    try {
      await this.readQueueSummary();
    } catch (error) {
      this.setQueueError(apiErrors.fromException(error, 'Não foi possível consultar a fila.'));
    }
  }

  renderQueueSummary(summary) {
    this.queueSummary.hidden = false;
    this.queueSummary.innerHTML = `
      <span><strong>${summary.total}</strong> preparados</span>
      <span><strong>${summary.pending}</strong> pendentes</span>
      <span><strong>${summary.sent}</strong> enviados</span>
      <span><strong>${summary.errors}</strong> erros</span>`;
    this.clearQueueButton.hidden = summary.total === 0;
    this.prepareQueueButton.disabled = summary.total > 0;
    this.queueAssociative.disabled = summary.total > 0;
    this.queueFunctional.disabled = summary.total > 0;
    this.queueProfile.disabled = summary.total > 0;
    this.queueTestEmail.disabled = summary.total > 0;
  }

  async readQueueSummary() {
    const response = await this.request(`/campaigns/${this.selectedCampaignId}/queue`);
    if (!response.ok) throw new Error(await apiErrors.fromResponse(response, 'Não foi possível consultar a fila.'));
    this.renderQueueSummary(await response.json());
  }

  async prepareQueue() {
    this.setQueueError();
    this.prepareQueueButton.disabled = true;
    this.queueAssociative.disabled = true;
    this.queueFunctional.disabled = true;
    this.queueProfile.disabled = true;
    this.queueTestEmail.disabled = true;
    this.queueProgressBox.hidden = false;
    this.queueSummary.hidden = true;
    this.queueProgress.value = 0;
    this.queueProgressText.textContent = '0 de 0';
    this.queueProgressPercent.textContent = '0%';
    this.queueProgressDetail.textContent = 'Contando destinatários...';

    try {
      const startResponse = await this.request(`/campaigns/${this.selectedCampaignId}/queue/prepare/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          associative_code: this.queueAssociative.value || null,
          functional_code: this.queueFunctional.value || null,
          profile_code: this.queueProfile.value || null,
          test_email: this.queueTestEmail.value.trim() || null,
        }),
      });
      if (!startResponse.ok) throw new Error(await apiErrors.fromResponse(startResponse, 'Não foi possível iniciar a preparação da fila.'));
      const start = await startResponse.json();

      const total = start.target_total;
      if (total === 0) {
        this.queueProgress.value = 100;
        this.queueProgressText.textContent = '0 de 0';
        this.queueProgressPercent.textContent = '100%';
        this.queueProgressDetail.textContent = 'Nenhum destinatário elegível encontrado.';
        await this.readQueueSummary();
        return;
      }

      let done = false;
      while (!done) {
        const batchResponse = await this.request(`/campaigns/${this.selectedCampaignId}/queue/prepare/batch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            associative_code: start.associative_code,
            functional_code: start.functional_code,
            profile_code: start.profile_code,
            test_email: start.test_email,
            cutoff: start.cutoff,
            target_total: total,
            batch_size: 250,
          }),
        });
        if (!batchResponse.ok) throw new Error(await apiErrors.fromResponse(batchResponse, 'Não foi possível adicionar os destinatários à fila.'));
        const batch = await batchResponse.json();

        const current = Math.min(batch.total, total);
        const percent = total ? Math.min(100, Math.round((current / total) * 100)) : 100;
        this.queueProgress.value = percent;
        this.queueProgressText.textContent = `${current} de ${total}`;
        this.queueProgressPercent.textContent = `${percent}%`;
        this.queueProgressDetail.textContent = batch.done ? 'Fila preparada com sucesso.' : `Inseridos ${batch.inserted_now} neste lote...`;
        done = batch.done;
        await new Promise((resolve) => setTimeout(resolve, 80));
      }

      await this.readQueueSummary();
      this.showMessage('Fila de destinatários preparada com sucesso.', 'success');
    } catch (error) {
      this.setQueueError(apiErrors.fromException(error, 'Não foi possível preparar a fila.'));
      this.prepareQueueButton.disabled = false;
      this.queueAssociative.disabled = false;
      this.queueFunctional.disabled = false;
      this.queueProfile.disabled = false;
      this.queueTestEmail.disabled = false;
      try { await this.readQueueSummary(); } catch {}
    }
  }

  async clearQueue() {
    if (!window.confirm('Limpar todos os destinatários ainda não enviados desta campanha?')) return;
    this.clearQueueButton.disabled = true;
    this.setQueueError();
    try {
      const response = await this.request(`/campaigns/${this.selectedCampaignId}/queue`, { method: 'DELETE' });
      if (!response.ok) throw new Error(await apiErrors.fromResponse(response, 'Não foi possível limpar a fila.'));
      this.queueProgressBox.hidden = true;
      await this.readQueueSummary();
      this.prepareQueueButton.disabled = false;
      this.queueAssociative.disabled = false;
      this.queueFunctional.disabled = false;
      this.queueProfile.disabled = false;
      this.queueTestEmail.disabled = false;
      this.showMessage('Fila limpa com sucesso.', 'success');
    } catch (error) {
      this.setQueueError(apiErrors.fromException(error, 'Não foi possível limpar a fila.'));
    } finally {
      this.clearQueueButton.disabled = false;
    }
  }

  async loadRecipientFilters() {
    if (!this.queueAssociative || !this.queueFunctional || !this.queueProfile) return;
    this.queueAssociative.innerHTML = '<option value="">Todas</option>';
    this.queueFunctional.innerHTML = '<option value="">Todas</option>';
    this.queueProfile.innerHTML = '<option value="">Todos</option>';
    try {
      const response = await this.request('/recipient-filters');
      if (!response.ok) throw new Error(await apiErrors.fromResponse(response, 'Não foi possível carregar os filtros de destinatários.'));
      const data = await response.json();
      for (const item of data.associative || []) this.queueAssociative.add(new Option(item.name, item.code));
      for (const item of data.functional || []) this.queueFunctional.add(new Option(item.name, item.code));
      for (const item of data.profiles || []) this.queueProfile.add(new Option(item.name, item.code));
    } catch (error) {
      this.showMessage(apiErrors.fromException(error, 'Não foi possível carregar os filtros de destinatários.'));
    }
  }
}

if (!customElements.get(TAG_NAME)) customElements.define(TAG_NAME, OrbitalMail);
