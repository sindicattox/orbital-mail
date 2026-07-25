# Orbital Mail

Módulo de campanhas de e-mail nas portas 4102/8102.

## Contexto autenticado

O módulo não possui `MAIL_TENANT_CODE`. O `tenant_code` vem do contexto autenticado do Orbital e é aplicado em todas as operações da tabela `EMAIL_CAMPAIGN` e também na pasta das imagens.

Em modo remoto:

```env
AUTH_MODE=remote
ORBITAL_AUTH_CONTEXT_URL=http://127.0.0.1:8001/auth/context
```

Em `AUTH_MODE=disabled`, apenas para teste técnico via curl, envie o cabeçalho `X-Tenant-Code`. Nenhum tenant fica fixado no `.env`.

## Imagens

O diretório físico deve ficar fora do projeto:

```env
MAIL_UPLOAD_DIR=/home/daniel/Code/data/orbital-mail/uploads
```

A API separa os arquivos por tenant:

```text
/home/daniel/Code/data/orbital-mail/uploads/anpprev/<arquivo>
```

`MAIL_PUBLIC_UPLOAD_URL` é a base pública usada dentro do HTML. Localmente serve para preview. No servidor, configure uma URL HTTPS pública acessível pelos clientes de e-mail.

```env
MAIL_PUBLIC_UPLOAD_URL=https://mail.seudominio.org/uploads/mail
```

## Executar

```bash
cd /home/daniel/Code/orgs/orbital/orbital-mail
./deploy/local/setup.sh
./deploy/local/start.sh
```

## MVP de destinatários

Na lista de campanhas, a ação **Destinatários** prepara a `EMAIL_QUEUE` existente em lotes de 250 registros.

Públicos iniciais:

- todos com e-mail válido;
- ativos;
- desfiliados (`MEMBER.BR_SITUACAO_ASSOCIATIVA_CODE = 'desfiliado'`).

O progresso é exibido como `inseridos X de Y`. Os registros são gravados com `STATUS = 'pending'`. A preparação:

- usa o `tenant_code` do contexto autenticado;
- ignora e-mails da `EMAIL_BLACKLIST`;
- remove duplicidade por e-mail dentro da campanha;
- usa uma data de corte para não incluir membros criados ou alterados depois do início;
- pode ser limpa e refeita enquanto não houver itens `processing` ou `sent`.

Esta etapa não envia e-mails. O worker de envio será implementado depois.
