# Relatório de testes

- `python3 -m compileall -q apps/api`: aprovado.
- `pytest -q`: **1068 testes aprovados**.
- `node --check apps/web/src/components/orbital-html-editor/editor.js`: aprovado.
- `node --check apps/web/src/assets/auth/orbital-mail-auth.js`: aprovado.
- `bash -n deploy/remote/test-public-image.sh`: aprovado.
- Smoke test local com Uvicorn real, arquivo temporário e download HTTP pela rota pública: aprovado.

## Contratos cobertos

- fallback standalone pelos três campos `AUTH_DEV_*`;
- sessão remota assinada com tenant recebido do Orbital;
- isolamento físico das imagens por tenant;
- rota pública canônica `/api/mail/uploads/{tenant}/{arquivo}`;
- rejeição no startup da configuração incorreta `/uploads/mail`;
- aceitação da URL HTTPS pública correta em configuração de produção;
- rejeição de localhost/127.0.0.1 em produção;
- retorno HTTP 200, `Content-Type: image/png` e bytes idênticos ao arquivo físico.

## Limite da validação

Nginx, DNS e certificado HTTPS do servidor do usuário não estão acessíveis neste ambiente. O projeto inclui `deploy/remote/test-public-image.sh` para executar o teste completo no servidor após o deploy.
