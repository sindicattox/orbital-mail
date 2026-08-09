# Descadastro por destinatário e tenant

## Contrato

1. O worker gera um token HMAC com e-mail, tenant e campanha.
2. O rodapé aponta para /orbital-mail/unsubscribe?token=....
3. A página pública mostra o e-mail mascarado e pede confirmação.
4. A confirmação grava ou atualiza EMAIL_BLACKLIST somente no tenant do token.
5. Cliques repetidos são idempotentes.
6. SMTP e SMTP2GO recebem List-Unsubscribe e List-Unsubscribe-Post.

O tenant nunca é aceito livremente do navegador. Alterar e-mail, tenant ou campanha invalida a assinatura. O token não expira para manter links antigos funcionais; por isso a chave deve ser estável.

## URLs por ambiente

Local:

~~~env
MAIL_PUBLIC_URL=https://admin.localhost/orbital-mail
EMAIL_UPLOAD_PUBLIC_URL=https://admin.localhost/orbital-mail/api/mail/uploads
~~~

Produção:

~~~env
MAIL_PUBLIC_URL=https://admin.sindicatto.com/orbital-mail
EMAIL_UPLOAD_PUBLIC_URL=https://admin.sindicatto.com/orbital-mail/api/mail/uploads
~~~

Apenas o domínio muda. O startup exige que protocolo e domínio das duas variáveis sejam iguais.

## Chave

~~~env
MAIL_UNSUBSCRIBE_SECRET=CHAVE_FORTE_E_ESTAVEL_DO_AMBIENTE
~~~

Gere com:

~~~bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
~~~

Produção não inicia sem a chave. Uma troca invalida todos os links emitidos com a chave anterior.

## Banco

O descadastro usa as colunas de EMAIL_BLACKLIST previstas em database/oracle/002_email_delivery_events.sql:

- TENANT_CODE
- SOURCE
- PERMANENT
- UPDATED_AT

A gravação usa SOURCE='unsubscribe' e PERMANENT=1, sempre com correspondência estrita de tenant.
