# Teste local por etapas

Execute uma etapa por vez e pare caso apareça erro.

## Etapa 1 — conferir arquivos privados

Confirme que estes arquivos continuam no seu projeto local e não vieram do ZIP:

```bash
ls -la apps/api/.env apps/web/.env apps/api/.emails_para_teste
```


## Etapa 2 — confirmar o fallback standalone

Em `apps/api/.env`:

```env
AUTH_MODE=disabled
AUTH_DEV_TENANT_CODE=anpprev
AUTH_DEV_USER_ID=1
AUTH_DEV_IS_ADMIN=true
```

Nesse modo o `orbital-app` não precisa estar iniciado.

## Etapa 3 — banco

A migração `database/oracle/002_email_delivery_events.sql` deve ser executada somente uma vez.
Se ela já foi executada e as constraints novas estão ENABLED, não execute novamente.

## Etapa 4 — iniciar

```bash
cd /home/daniel/Code/orgs/orbital/orbital-mail
./deploy/local/start.sh
```

## Etapa 5 — saúde da API

```bash
curl -i http://127.0.0.1:8104/api/health
```

Esperado: HTTP 200.


## Etapa 6 — imagem pública local

No `apps/api/.env`, confirme exatamente:

```env
EMAIL_UPLOAD_DIR=/home/daniel/storage/tenants/{tenant}/media/email_campaign
EMAIL_UPLOAD_PUBLIC_URL=http://127.0.0.1:8104/api/mail/uploads
```

Não use `/uploads/mail`. Reinicie a API, insira uma imagem nova no editor e confira no DevTools que o `Request URL` começa com:

```text
http://127.0.0.1:8104/api/mail/uploads/
```

A rota não depende de CORS e deve responder HTTP 200.

## Etapa 7 — teste mínimo

Na página `/teste-loop`, use:

- 1 endereço autorizado
- 1 repetição
- 1 worker
- provedor SMTP/SES ou SMTP2GO

A campanha deve terminar como `completed` ou mostrar erro classificado.

## Etapa 8 — teste controlado

Depois do teste mínimo:

- 6 endereços
- 1 repetição
- 1 worker

## Etapa 9 — concorrência

Somente depois das etapas anteriores:

- 6 endereços
- 1 repetição
- 2 workers

## Etapa 10 — conferir banco

```sql
SELECT status, provider_status, last_error_class, retryable, blocked,
       try_count, provider_message_id, error
  FROM email_queue
 ORDER BY id DESC
 FETCH FIRST 20 ROWS ONLY;

SELECT status, event_type, provider, error_class, retryable,
       provider_message_id, error, event_at
  FROM email_send_log
 ORDER BY id DESC
 FETCH FIRST 30 ROWS ONLY;
```
