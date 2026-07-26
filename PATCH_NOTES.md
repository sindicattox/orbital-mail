# Correção da URL pública das imagens

- Mantida a rota pública real: `/api/mail/uploads/{tenant}/{arquivo}`.
- `EMAIL_UPLOAD_PUBLIC_URL` agora é validada no startup e precisa terminar exatamente em `/api/mail/uploads`.
- A configuração incorreta `/uploads/mail` é rejeitada antes que novas imagens quebradas sejam gravadas no HTML.
- Produção continua exigindo HTTPS público e rejeitando localhost/127.0.0.1.
- Incluído `deploy/remote/test-public-image.sh`, que valida Nginx/HTTPS → API → storage do tenant com uma imagem temporária.
- Nenhuma alteração no `orbital-app`.

# Patch de tratamento de erros e eventos

## Ordem de aplicação

1. Preserve `./.env` e `apps/api/.emails_para_teste` existentes.
2. Execute `database/oracle/002_email_delivery_events.sql` no schema `WKSP_SINDICATTO`.
3. Substitua os arquivos do projeto.
4. Reinicie o aplicativo.

## Alterações

- Remove `EMAIL_CAMPAIGN_RECIPIENT` depois de criar `EMAIL_CAMPAIGN_RECIPIENT_BKP`.
- `EMAIL_QUEUE` passa a guardar provedor, estado do provedor, classe do erro, retry e entrega.
- `EMAIL_SEND_LOG` passa a registrar tentativas e eventos com diagnóstico bruto.
- `EMAIL_BLACKLIST` passa a aceitar bloqueio global ou por tenant.
- Respostas imediatas dos provedores são classificadas como destinatário, temporárias, configuração ou provedor.
- Erros definitivos de destinatário são bloqueados; erros temporários respeitam o limite de tentativas.
- Erros de configuração encerram o processamento sem bloquear destinatários válidos.

## Limite desta entrega

Este patch trata respostas imediatas durante o envio. Webhooks posteriores de `delivered`, bounce, complaint e unsubscribe ainda precisam ser conectados aos provedores na próxima etapa.

## 2026-07-25 — imagens públicas multi-tenant

- `AUTH_DEV_TENANT_CODE` continua sendo o único seletor de tenant no modo local independente.
- Em produção, o tenant continua vindo exclusivamente do contexto autenticado (`AUTH_MODE=remote`).
- `EMAIL_UPLOAD_DIR` agora resolve corretamente o marcador `{tenant}`.
- As imagens públicas são servidas em `/api/mail/uploads/{tenant}/{arquivo}`, aproveitando o proxy já usado pelo módulo.
- `EMAIL_UPLOAD_PUBLIC_URL` é validada em produção: deve usar HTTPS e não pode apontar para localhost/127.0.0.1.
- Removido da distribuição o arquivo privado `apps/api/.emails_para_teste`.

## 2026-07-25 — contexto do Orbital sem alterar o orbital-app

- Alteração restrita ao `orbital-mail`.
- `AUTH_MODE=disabled` usa exatamente `AUTH_DEV_TENANT_CODE`, `AUTH_DEV_USER_ID` e `AUTH_DEV_IS_ADMIN`.
- `AUTH_MODE=remote` ignora os fallbacks e usa a identidade retornada pelo SSO já existente no Orbital.
- A identidade remota é armazenada em cookie próprio, assinado, `HttpOnly` e com expiração.
- O frontend redireciona para o SSO somente após uma resposta `401` da API do Mail.
- Mantida compatibilidade opcional com `AUTH_CONTEXT_URL` para Bearer/proxy legado.
- Uploads e campanhas continuam sempre filtrados por `auth.tenant_code`.
