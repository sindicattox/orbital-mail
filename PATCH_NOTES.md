# Patch de tratamento de erros e eventos

## Ordem de aplicação

1. Preserve `apps/api/.env` e `apps/api/.emails_para_teste` existentes.
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
