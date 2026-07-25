# Teste local por etapas

Execute uma etapa por vez e pare caso apareça erro.

## Etapa 1 — conferir arquivos privados

Confirme que estes arquivos continuam no seu projeto local e não vieram do ZIP:

```bash
ls -la apps/api/.env apps/api/.emails_para_teste
```

## Etapa 2 — banco

A migração `database/oracle/002_email_delivery_events.sql` deve ser executada somente uma vez.
Se ela já foi executada e as constraints novas estão ENABLED, não execute novamente.

## Etapa 3 — iniciar

```bash
cd /home/daniel/Code/orgs/orbital/orbital-mail
./deploy/local/start.sh
```

## Etapa 4 — saúde da API

```bash
curl -i http://127.0.0.1:8102/api/health
```

Esperado: HTTP 200.

## Etapa 5 — teste mínimo

Na página `/teste-loop`, use:

- 1 endereço autorizado
- 1 repetição
- 1 worker
- provedor SMTP/SES ou SMTP2GO

A campanha deve terminar como `completed` ou mostrar erro classificado.

## Etapa 6 — teste controlado

Depois do teste mínimo:

- 6 endereços
- 1 repetição
- 1 worker

## Etapa 7 — concorrência

Somente depois das etapas anteriores:

- 6 endereços
- 1 repetição
- 2 workers

## Etapa 8 — conferir banco

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
