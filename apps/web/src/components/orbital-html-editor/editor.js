const ALLOWED_IMAGE_TYPES = new Set([
  'image/png',
  'image/jpeg',
  'image/webp',
  'image/gif',
]);

class OrbitalHtmlEditor extends HTMLElement {
  connectedCallback() {
    if (this.dataset.ready === 'true') return;
    this.dataset.ready = 'true';

    this.content = this.querySelector('[data-editor-content]');
    this.source = this.querySelector('[data-editor-source]');
    this.valueField = this.querySelector('[data-editor-value]');
    this.status = this.querySelector('[data-editor-status]');
    this.fileInput = this.querySelector('[data-image-input]');
    this.savedRange = null;
    this.sourceMode = false;
    this.content.innerHTML = this.valueField.value || '';

    this.bindEvents();
    this.updateToolbarState();
  }

  get value() {
    return this.sourceMode ? this.source.value : this.content.innerHTML;
  }

  set value(html) {
    const safeValue = html || '';
    this.content.innerHTML = safeValue;
    this.source.value = safeValue;
    this.valueField.value = safeValue;
    this.updateToolbarState();
  }

  bindEvents() {
    ['keyup', 'mouseup', 'input', 'focus'].forEach((type) => {
      this.content.addEventListener(type, () => {
        this.saveSelection();
        if (type === 'input') this.syncValue();
        this.updateToolbarState();
      });
    });

    this.querySelectorAll('[data-command]').forEach((button) => {
      button.addEventListener('mousedown', (event) => {
        event.preventDefault();
        this.restoreSelection();
        document.execCommand(button.dataset.command, false);
        this.saveSelection();
        this.syncValue();
        this.updateToolbarState();
      });
    });

    this.querySelectorAll('[data-block]').forEach((button) => {
      button.addEventListener('mousedown', (event) => {
        event.preventDefault();
        this.restoreSelection();
        document.execCommand('formatBlock', false, button.dataset.block);
        this.saveSelection();
        this.syncValue();
        this.updateToolbarState();
      });
    });

    this.querySelector('[data-action="link"]').addEventListener('click', () => this.insertLink());
    this.querySelector('[data-action="image"]').addEventListener('click', () => {
      this.saveSelection();
      this.fileInput.click();
    });
    this.querySelector('[data-action="source"]').addEventListener('click', (event) => {
      this.toggleSource(event.currentTarget);
    });

    this.fileInput.addEventListener('change', async () => {
      const file = this.fileInput.files?.[0];
      if (file) await this.uploadAndInsert(file);
      this.fileInput.value = '';
    });

    this.content.addEventListener('paste', async (event) => {
      const image = Array.from(event.clipboardData?.files || []).find((file) =>
        file.type.startsWith('image/'),
      );
      if (!image) return;

      event.preventDefault();
      this.saveSelection();
      await this.uploadAndInsert(image);
    });

    this.source.addEventListener('input', () => this.syncValue());

    document.addEventListener('selectionchange', () => {
      const selection = window.getSelection();
      if (!selection?.rangeCount) return;
      const node = selection.anchorNode;
      if (node && this.content.contains(node)) {
        this.saveSelection();
        this.updateToolbarState();
      }
    });
  }

  saveSelection() {
    const selection = window.getSelection();
    if (!selection?.rangeCount) return;
    const range = selection.getRangeAt(0);
    if (this.content.contains(range.commonAncestorContainer)) {
      this.savedRange = range.cloneRange();
    }
  }

  restoreSelection() {
    this.content.focus();
    if (!this.savedRange) return;
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(this.savedRange);
  }

  syncValue() {
    this.valueField.value = this.value;
    this.dispatchEvent(
      new CustomEvent('editor-change', {
        detail: { html: this.value },
        bubbles: true,
      }),
    );
  }

  insertLink() {
    this.restoreSelection();
    const url = window.prompt('URL do link:');
    if (!url) return;
    if (!/^https?:\/\//i.test(url) && !/^mailto:/i.test(url)) {
      this.setStatus('Use uma URL iniciada por http://, https:// ou mailto:.', true);
      return;
    }
    document.execCommand('createLink', false, url);
    this.saveSelection();
    this.syncValue();
    this.updateToolbarState();
  }

  toggleSource(button) {
    this.sourceMode = !this.sourceMode;
    if (this.sourceMode) {
      this.source.value = this.content.innerHTML;
      this.content.hidden = true;
      this.source.hidden = false;
      button.classList.add('is-active');
      button.setAttribute('aria-pressed', 'true');
      this.source.focus();
    } else {
      this.content.innerHTML = this.source.value;
      this.source.hidden = true;
      this.content.hidden = false;
      button.classList.remove('is-active');
      button.setAttribute('aria-pressed', 'false');
      this.content.focus();
    }
    this.syncValue();
    this.updateToolbarState();
  }

  async uploadAndInsert(file) {
    if (!ALLOWED_IMAGE_TYPES.has(file.type)) {
      this.setStatus('Formato não permitido. Use PNG, JPG, WEBP ou GIF.', true);
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      this.setStatus('A imagem deve ter no máximo 5 MB.', true);
      return;
    }

    const uploadUrl = this.getAttribute('upload-url');
    if (!uploadUrl) {
      this.setStatus('URL de upload não configurada.', true);
      return;
    }

    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 30_000);
    this.setBusy(true, 'Enviando imagem...');

    try {
      const body = new FormData();
      body.append('file', file);
      const response = await fetch(uploadUrl, {
        method: 'POST',
        body,
        credentials: 'include',
        signal: controller.signal,
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(result.detail || `Falha ao enviar imagem (${response.status}).`);
      }
      if (!result.url) throw new Error('A API não retornou a URL da imagem.');

      this.restoreSelection();
      const image = document.createElement('img');
      image.src = result.url;
      image.alt = file.name || 'Imagem da campanha';
      image.loading = 'lazy';
      this.insertNode(image);
      this.syncValue();
      this.setStatus('Imagem inserida. Ela foi salva na área pública do tenant.');
    } catch (error) {
      const message = error?.name === 'AbortError'
        ? 'O upload excedeu 30 segundos.'
        : error?.message || 'Falha ao enviar imagem.';
      this.setStatus(message, true);
    } finally {
      window.clearTimeout(timeoutId);
      this.setBusy(false);
    }
  }

  insertNode(node) {
    const selection = window.getSelection();
    if (selection?.rangeCount) {
      const range = selection.getRangeAt(0);
      range.deleteContents();
      range.insertNode(node);
      range.setStartAfter(node);
      range.collapse(true);
      selection.removeAllRanges();
      selection.addRange(range);
    } else {
      this.content.appendChild(node);
    }
    this.savedRange = null;
    this.content.focus();
  }

  updateToolbarState() {
    if (this.sourceMode) return;

    const commandStates = {
      bold: document.queryCommandState('bold'),
      italic: document.queryCommandState('italic'),
      underline: document.queryCommandState('underline'),
      insertUnorderedList: document.queryCommandState('insertUnorderedList'),
    };

    this.querySelectorAll('[data-command]').forEach((button) => {
      const active = Boolean(commandStates[button.dataset.command]);
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });

    const block = String(document.queryCommandValue('formatBlock') || '')
      .replace(/[<>]/g, '')
      .toLowerCase();
    this.querySelectorAll('[data-block]').forEach((button) => {
      const active = block === button.dataset.block.toLowerCase();
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
  }

  setBusy(busy, text) {
    this.querySelectorAll('button').forEach((button) => {
      button.disabled = busy;
    });
    if (text) this.setStatus(text);
  }

  setStatus(text, error = false) {
    this.status.textContent = text;
    this.status.classList.toggle('is-error', error);
  }
}

if (!customElements.get('orbital-html-editor')) {
  customElements.define('orbital-html-editor', OrbitalHtmlEditor);
}
