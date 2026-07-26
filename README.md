# Orbital Mail

Módulo independente de campanhas e envio de e-mails do ecossistema Orbital.

## Tenant e autenticação

O `orbital-mail` possui dois modos explícitos. Não existe `MAIL_TENANT_CODE` e o frontend nunca escolhe ou envia o tenant.

### 1. Standalone local

Use para desenvolver e testar o Mail sem iniciar o `orbital-app`:

```env
AUTH_MODE=disabled
AUTH_DEV_TENANT_CODE=anpprev
AUTH_DEV_USER_ID=1
AUTH_DEV_IS_ADMIN=true
```

Nesse modo, os três valores acima formam o contexto técnico local. Nenhuma chamada de autenticação é feita ao Orbital.

### 2. Conectado ao Orbital

```env
AUTH_MODE=remote
AUTH_AUTHORIZE_URL=http://127.0.0.1:4001/auth/sso/authorize
AUTH_TOKEN_URL=http://127.0.0.1:8001/auth/sso/token
AUTH_CLIENT_ID=email-app
AUTH_CLIENT_SECRET=...
AUTH_REDIRECT_URI=http://127.0.0.1:8104/api/mail/auth/callback
AUTH_WEB_URL=http://127.0.0.1:4104/
AUTH_SESSION_SECRET=...
AUTH_COOKIE_SECURE=false
```

O Mail usa o SSO já existente no `orbital-app`:

1. a Web do Mail recebe `401` quando ainda não há sessão;
2. o Mail redireciona para `/auth/sso/authorize` do Orbital;
3. o Orbital devolve uma identidade temporária com `member_id`, `tenant_code`, perfil e flags;
4. o Mail grava essa identidade em cookie próprio, assinado e `HttpOnly`;
5. campanhas, filas, destinatários e uploads usam somente `auth.tenant_code`.

`AUTH_DEV_TENANT_CODE`, `AUTH_DEV_USER_ID` e `AUTH_DEV_IS_ADMIN` são ignorados em `AUTH_MODE=remote`.

O `AUTH_REDIRECT_URI` deve ser o callback do Mail já autorizado para o cliente `email-app`. Isso é configuração de integração; nenhuma alteração de código no `orbital-app` faz parte desta entrega.

## Imagens públicas multi-tenant

```env
EMAIL_UPLOAD_DIR=/home/daniel/storage/tenants/{tenant}/media/email_campaign
EMAIL_UPLOAD_PUBLIC_URL=http://127.0.0.1:8104/api/mail/uploads
```

O marcador `{tenant}` é resolvido pelo contexto atual:

```text
/home/daniel/storage/tenants/anpprev/media/email_campaign/<uuid>.png
```

A URL inserida no HTML do e-mail é pública e não exige login:

```text
http://127.0.0.1:8104/api/mail/uploads/anpprev/<uuid>.png
```

Em produção, `EMAIL_UPLOAD_PUBLIC_URL` precisa usar HTTPS público.

O caminho público é fixo e canônico:

```text
/api/mail/uploads
```

A configuração antiga/incorreta abaixo é rejeitada no startup para não gravar imagens quebradas no HTML:

```env
EMAIL_UPLOAD_PUBLIC_URL=http://127.0.0.1:8104/uploads/mail
```

Configurações corretas:

```env
# Local
EMAIL_UPLOAD_PUBLIC_URL=http://127.0.0.1:8104/api/mail/uploads

# Produção
EMAIL_UPLOAD_PUBLIC_URL=https://email.seudominio.org/api/mail/uploads
```

Não é CORS: a imagem é um `GET` público. Um `404` em `/uploads/mail/...` indica apenas caminho público incompatível.

### Smoke test de produção

Depois que Nginx, HTTPS, API e storage estiverem ativos, execute no servidor:

```bash
cd /home/ubuntu/apps/orbital-mail
./deploy/remote/test-public-image.sh anpprev
```

O teste cria uma imagem PNG temporária no storage do tenant, acessa a URL HTTPS pública, confere HTTP 200, `Content-Type: image/png` e os bytes retornados, e remove o arquivo ao terminar.

O Nginx deve encaminhar a rota canônica para a API, sem expor a pasta com `alias`:

```nginx
location /api/mail/ {
    proxy_pass http://127.0.0.1:8104/api/mail/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Execução local

```bash
./deploy/local/setup.sh
./deploy/local/start.sh
```

A Web usa a porta `4104` e a API usa `8104`.
