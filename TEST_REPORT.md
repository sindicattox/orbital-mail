# Relatório de testes

- `python3 -m compileall -q apps/api`: aprovado.
- `python3 -m pytest -q`: **1071 testes aprovados**.
- `node --check` no Web Component público, auxiliares, editor e autenticação: aprovado.
- `bash -n` em todos os scripts de deploy local e remoto: aprovado.
- `package-lock.json` atualizado com `@orbital/ui`: aprovado.

## Contratos cobertos

- barra standalone fornecida por `@orbital/ui`, sem cópia local;
- Web Component público `<orbital-mail>` reutilizado pela página standalone e pelo `orbital-app`;
- API própria configurável por `api-base` e rotas standalone configuráveis por `base-url`;
- sessão por cookie, credenciais incluídas e início do SSO em respostas `401`;
- evento público `orbital-module-error` compatível com o carregador do `orbital-app`;
- fallback standalone pelos três campos `AUTH_DEV_*`;
- sessão remota assinada com tenant recebido do Orbital;
- isolamento físico das imagens por tenant;
- rota pública canônica `/api/mail/uploads/{tenant}/{arquivo}`;
- rejeição no startup da configuração incorreta `/uploads/mail`;
- deploy remoto padronizado, sem envio automático dos arquivos `.env`;
- caminho remoto `/home/ubuntu/apps/orbital/orbital-mail` nos serviços e scripts;
- arquivo privado `.emails_para_teste` ausente do pacote.

## Validação do build

O `npm ci` não pôde ser concluído neste ambiente porque o registry configurado respondeu HTTP 503. Por isso, `astro check` e `astro build` não foram executados aqui. Os scripts `deploy/local/test.sh` e `deploy/remote/setup-web.sh` executam obrigatoriamente ambos e interrompem o processo se houver erro.
