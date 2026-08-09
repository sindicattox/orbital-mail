# Contrato de Deploy

## Deploy local e remoto são iguais

- `setup.sh` chama `setup-api.sh` e `setup-web.sh`.
- `setup-api.sh` para os serviços conhecidos da API, libera apenas as portas configuradas que permanecem ocupadas por processos órfãos, limpa e prepara a API e eventuais workers do módulo, e então chama `start-api.sh`.
- `setup-web.sh` para o serviço web conhecido, libera apenas as portas configuradas que permanecem ocupadas por processos órfãos, limpa e prepara a aplicação web, e então chama `start-web.sh`.
- `start.sh` chama `start-api.sh` e `start-web.sh`.
- `start-api.sh` apenas inicia e valida a API e eventuais workers.
- `start-web.sh` apenas inicia e valida a aplicação web.
- `test.sh` chama os testes secundários aplicáveis ao módulo.
- Podem existir testes secundários com o padrão `test-*.sh`.
- A API e a Web carregam suas próprias configurações em `apps/api/config` e `apps/web/config`.
- O deploy copia normalmente os envs local e produção.
- O deploy seleciona `config/runtime`: local aponta para `local` e remoto aponta para `production`.
- API e Web leem somente `config/runtime`; a aplicação não detecta ambiente por caminho, hostname ou condição de código.
- O código de deploy deve ser simples, enxuto, legível e livre de arquivos, funções, comentários ou lógica sem uso.
- Todos os scripts devem informar claramente no terminal o que estão fazendo e o resultado de cada etapa.

## Diferenças do remoto

- `setup.sh` envia os arquivos com `rsync`, ignorando pastas e arquivos que não precisam subir, e depois chama `setup-api.sh` e `setup-web.sh`.
- A aplicação remota usa `apps/api/config/production` e `apps/web/config/production`.
- Arquivos exclusivos do remoto, como `target.conf` e `wallet-upload.sh`, ficam em `deploy/remote`.
