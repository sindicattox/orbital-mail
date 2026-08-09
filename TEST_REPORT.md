# Relatório de validação

Data: 2026-08-09

## Orbital Mail

- Python compileall: aprovado.
- Pytest: 1123 testes aprovados.
- Astro check: 0 erros, 0 warnings e 16 hints.
- Astro build SSR/Node: aprovado.
- Sintaxe dos scripts deploy/local e deploy/remote: aprovada.
- git diff --check: aprovado.
- Config local: development, auth remote, Oracle e chave de descadastro válidos.
- Config produção: production, auth remote, Oracle, URLs HTTPS públicas e chave de descadastro válidos.

## Integração local

Com o Orbital App ativo:

- API Mail /api/health: HTTP 200.
- Web Mail /orbital-mail/: HTTP 200.
- Contexto sem token: HTTP 401.
- Gateway https://admin.localhost/orbital-mail/: HTTP 200.
- Contexto pelo gateway sem token: HTTP 401.
- Os processos temporários do Mail foram encerrados após o smoke test.

## Orbital App

- Testes focados de contexto de módulo, MenuService e permissões Oracle: 10 aprovados.
- Build da Web: aprovado.
- Suíte ampla da API: 281 aprovados e 8 falhas fora do alinhamento do Mail.

As oito falhas amplas já existentes envolvem credenciais do teste de login real, nota clonada, uso de SYSTIMESTAMP, auditorias de scripts de pool ausentes e um teste dependente do diretório de execução. Os testes modificados pela integração Mail/App estão verdes.

## Contratos cobertos

- mesma árvore local/production do Orbital App;
- mesmos loaders de configuração do Orbital App;
- deploy local/remoto alinhado e sem config/runtime;
- autenticação remota obrigatória nos dois ambientes;
- autorização orbital-mail-home/access_page centralizada no Orbital App;
- tenant recebido somente do contexto autenticado;
- lista privada .emails_para_teste excluída do rsync;
- imagem pública com rota canônica e isolamento físico por tenant;
- imagem e descadastro no mesmo protocolo/domínio;
- caminhos públicos idênticos local/remoto, variando o domínio;
- chave HMAC de descadastro obrigatória em produção;
- smoke test remoto de imagem compatível com config/{local,production}.

## Validações ainda dependentes do servidor

Antes do go-live definitivo:

1. executar deploy/remote/setup.sh;
2. executar deploy/remote/test.sh;
3. autenticar um usuário real com a permissão orbital-mail-home/access_page;
4. executar deploy/remote/test-public-image.sh com um tenant real;
5. enviar uma mensagem controlada e testar imagem e os dois links de descadastro.
