# Descadastro por destinatário e por tenant

## Escopo desta entrega

Implementação isolada do descadastro. Não altera campanhas, editor, autenticação, fila, filtros ou deploy.

## Funcionamento

1. O worker gera um token HMAC com e-mail, tenant e campanha.
2. O rodapé recebe um link público `/unsubscribe?token=...`.
3. A página mostra o e-mail mascarado e o tenant e pede confirmação.
4. A confirmação grava ou atualiza `EMAIL_BLACKLIST` somente para o `TENANT_CODE` do token.
5. Cliques repetidos são idempotentes.
6. SMTP e SMTP2GO recebem `List-Unsubscribe` e `List-Unsubscribe-Post` para descadastro de um clique.

## Segurança

- O tenant não é recebido livremente do navegador.
- Alterar e-mail, tenant ou campanha invalida a assinatura.
- O token não expira para que links antigos de descadastro continuem válidos.
- A chave não fica no código nem no banco.

## Configuração local

Adicionar em `apps/api/.env`:

```env
MAIL_PUBLIC_URL=http://127.0.0.1:4106
MAIL_UNSUBSCRIBE_SECRET=gere-uma-chave-longa-e-aleatoria
```

Exemplo para gerar a chave:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Configuração remota futura

```env
MAIL_PUBLIC_URL=https://orbital-mail.asaclub.org.br
MAIL_UNSUBSCRIBE_SECRET=CHAVE_FORTE_DO_AMBIENTE
```

## Banco

Esta implementação usa as colunas de `EMAIL_BLACKLIST` já previstas em `database/oracle/002_email_delivery_events.sql`:

- `TENANT_CODE`
- `SOURCE`
- `PERMANENT`
- `UPDATED_AT`

O descadastro grava `SOURCE='unsubscribe'` e `PERMANENT=1`.

## Testes

- Testes focados: 28 aprovados.
- Suíte completa: 1092 aprovados e 5 falhas preexistentes no ZIP original, ligadas a arquivos antigos de deploy/autenticação.
- Compilação Python: aprovada.
- Build web não pôde ser executado neste ambiente porque o registry interno retornou 404 para `zwitch-2.0.4`; o arquivo Astro foi validado pelos testes de contrato.
