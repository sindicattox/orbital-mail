# Orbital Mail

Módulo de campanhas e envio de e-mails do ecossistema Orbital.

O orbital-app é a fonte de verdade para deploy, configuração, sessão, tenant e autorização. O Mail mantém a mesma estrutura apps/{api,web}/config/{local,production} e os mesmos scripts deploy/{local,remote}. As diferenças se limitam ao nome do serviço, portas, workers e variáveis próprias de e-mail.

## Ambientes e configuração

A seleção de ambiente é idêntica à do Orbital App:

- sob /home/daniel/, API e Web carregam config/local;
- nos demais caminhos, carregam config/production;
- não existe config/runtime, symlink de seleção ou segundo loader;
- os envs reais contêm credenciais e permanecem fora do Git.

Arquivos obrigatórios da API:

~~~text
apps/api/config/local/app.env
apps/api/config/local/auth.env
apps/api/config/local/database.env
apps/api/config/local/services.env
apps/api/config/production/app.env
apps/api/config/production/auth.env
apps/api/config/production/database.env
apps/api/config/production/services.env
~~~

A Web segue a mesma estrutura com app.env e services.env.

Local mantém o padrão do App (APP_ENV=development, bind 0.0.0.0). Produção usa APP_ENV=production e bind 127.0.0.1. O banco é Oracle nos dois ambientes; apenas credenciais, wallet e caminhos físicos próprios do servidor podem variar.

## Autenticação e autorização

Não existe modo standalone ou tenant configurado no frontend. Local e produção usam obrigatoriamente:

~~~env
AUTH_CONTEXT_URL=http://127.0.0.1:8001/auth/context/module
AUTH_MODE=remote
AUTH_TIMEOUT_SECONDS=5
~~~

Fluxo:

1. o usuário entra pelo Orbital App;
2. a Web do Mail reutiliza orbitalSession no mesmo domínio e envia o Bearer token;
3. a API do Mail consulta o contexto no Orbital App;
4. o Orbital App valida orbital-mail-home/access_page pelo MenuService;
5. o Mail usa exclusivamente tenant_code, usuário e flags devolvidos pelo App.

Sem token, a resposta é 401. Sem permissão do módulo, é 403. Admin não ignora a permissão do perfil; desenvolvedor continua limitado aos módulos habilitados para o tenant.

## Gateway público

O navegador nunca usa diretamente as portas 4106 ou 8106. API, páginas, imagens e descadastro passam pelo mesmo gateway:

~~~text
/orbital-mail/...
/orbital-mail/api/mail/...
~~~

Exemplo de proxy:

~~~nginx
location /orbital-mail/api/mail/ {
    proxy_pass http://127.0.0.1:8106/api/mail/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
~~~

A Web escuta em 4106; a API, em 8106.

## Imagens públicas multi-tenant

A estrutura física é a mesma nos dois ambientes:

~~~text
<storage>/tenants/{tenant}/media/email_campaign/<uuid>.<extensão>
~~~

Configuração local:

~~~env
EMAIL_UPLOAD_DIR=/home/daniel/storage/tenants/{tenant}/media/email_campaign
EMAIL_UPLOAD_PUBLIC_URL=https://admin.localhost/orbital-mail/api/mail/uploads
MAIL_PUBLIC_URL=https://admin.localhost/orbital-mail
~~~

Configuração remota:

~~~env
EMAIL_UPLOAD_DIR=/home/ubuntu/storage/tenants/{tenant}/media/email_campaign
EMAIL_UPLOAD_PUBLIC_URL=https://admin.sindicatto.com/orbital-mail/api/mail/uploads
MAIL_PUBLIC_URL=https://admin.sindicatto.com/orbital-mail
~~~

A lógica e os caminhos públicos são idênticos; mudam somente domínio e raiz física do servidor. O startup rejeita:

- rota diferente de /orbital-mail/api/mail/uploads;
- protocolo/domínio divergente entre imagem e Mail;
- endereço local ou HTTP em produção.

A leitura da imagem é pública, mas upload e gravação continuam autenticados e isolados pelo tenant.

## Descadastro

Os links usam o mesmo MAIL_PUBLIC_URL das imagens:

~~~text
https://<domínio>/orbital-mail/unsubscribe?token=...
https://<domínio>/orbital-mail/api/mail/public/unsubscribe?token=...
~~~

O token HMAC contém e-mail, tenant e campanha. MAIL_UNSUBSCRIBE_SECRET deve ser forte, estável e diferente entre ambientes. Em produção ela é obrigatória no startup; trocar a chave invalida links antigos.

Geração sugerida:

~~~bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
~~~

## Execução local

O Orbital App precisa estar ativo para autenticação e autorização:

~~~bash
./deploy/local/setup.sh
./deploy/local/test.sh
~~~

setup.sh prepara e inicia API e Web. start.sh apenas inicia instalações já preparadas.

## Deploy remoto

Configure deploy/remote/target.conf e os envs de produção reais antes do envio:

~~~bash
./deploy/remote/setup.sh
./deploy/remote/test.sh
./deploy/remote/test-public-image.sh anpprev
~~~

O deploy segue o Orbital App: sincroniza com rsync, prepara API/Web e reinicia os serviços. Wallet, ambientes virtuais, dependências geradas, logs e .emails_para_teste não são enviados.

O smoke test de imagem cria um PNG temporário no storage do tenant, consulta a URL HTTPS pública, valida status, tipo e bytes, e remove o arquivo ao terminar.

## Componente incorporável

~~~text
/orbital-mail/components/mail.js
<orbital-mail>
~~~

O componente reutiliza a gestão de campanhas e não renderiza uma segunda barra dentro do Orbital App.
