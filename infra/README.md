# 🚀 Infraestrutura e Deploy — Sora

Runbook de instalação, deploy e operação dos ambientes.

> **Nunca** comite `.env`, `.ghcr-token`, chaves privadas ou `acme.json`.
> O bootstrap gera o `.env` real com senhas alfanuméricas fortes e `chmod 600`.

---

## 1. Fluxo de Branches

```text
feature/* ──PR──> develop ──PR──> main
                     │              │
                     ▼              ▼
              imagem `develop`   imagem `latest`
              deploy automático  Portainer (manual)
```

| Branch | CI/CD | Ambiente |
| :--- | :--- | :--- |
| `feature/*` | Valida compose no PR | — |
| `develop` | Build `develop` + deploy automático | Desenvolvimento/Homologação |
| `main` | Build `latest` (sem deploy) | Produção via **Portainer** |
| tag `v*.*.*` | Build imutável `v1.2.3` | Rollback / release |

> O repositório usa `main` como branch de produção (equivalente ao "master").

---

## 2. Visão Geral

| Componente | Arquivo |
| :--- | :--- |
| Compose de desenvolvimento | `infra/compose/docker-compose.dev.yml` |
| Compose de produção | `infra/compose/docker-compose.prod.yml` |
| Overlay TLS wildcard (Cloudflare) | `infra/compose/docker-compose.tls-dns.yml` |
| Config estática do Traefik | `infra/traefik/traefik.yml` |
| Middlewares do Traefik | `infra/traefik/dynamic.yml` |
| Rotas locais de dev | `infra/traefik/dynamic-dev.yml` |
| Bootstrap do servidor | `infra/scripts/bootstrap-server.sh` |
| Deploy (dev/CLI) | `infra/scripts/deploy.sh` |
| Troca de domínio (DNS + rollback) | `infra/scripts/change-domain.sh` |
| Backup / Restore | `infra/scripts/backup-postgres.sh`, `restore-postgres.sh` |
| CI/CD | `.github/workflows/pipeline.yml` |

> **Supply chain:** as actions usam tags de major (`@v4`). Para produção rígida, fixe cada action em um commit SHA.

### Arquitetura de rede

```text
Internet
   │  80/443
┌──▼──────────┐
│   Traefik   │  rede: sora_edge
└──┬───────┬──┘
   │       │
┌──▼───┐ ┌─▼────┐
│ web  │ │ api  │  rede: sora_edge + sora_internal
└──────┘ └─┬────┘
           │
   ┌───────┴────────┐
┌──▼───────┐  ┌─────▼─────┐
│ postgres │  │   redis   │  rede: sora_internal (sem portas públicas)
└──────────┘  └───────────┘
```

- **PostgreSQL e Redis não publicam portas** — acessíveis apenas pela rede interna.
- **Traefik** é o único serviço exposto (80/443).
- API em `api.<domínio>` e Web em `app.<domínio>`.
- Subdomínio por clínica (`{clinica}.<domínio>`) exige o overlay de TLS wildcard.

> ⚠️ Os nomes de rede (`sora_edge`, `sora_internal`), volumes e portas 80/443 são fixos.
> **Não rode dev e produção no mesmo host** com estes arquivos — use servidores separados.

---

## 3. Desenvolvimento Local

```bash
cp .env.example .env
docker compose -f infra/compose/docker-compose.dev.yml up -d
```

Sobe Traefik + PostgreSQL 16 (com init do role RLS `sora_app`) + Redis 7 + MinIO (S3 local). API e Web rodam no host:

- API: `http://api.sora.localhost:8000`
- Painel Web: `http://app.sora.localhost:8000`
- Link Público (Slug ou Subdomínio): `http://sora.localhost:8000/{clinica}` ou `http://{clinica}.sora.localhost:8000`
- Dashboard Traefik: `http://localhost:8080`
- PostgreSQL: `127.0.0.1:5432` (`sora` p/ migrations DDL | `sora_app` com `NOBYPASSRLS` p/ API)
- Redis: `127.0.0.1:6379`
- MinIO S3 (Prontuários / Pre-signed URLs): `http://127.0.0.1:9000` (Console: `http://127.0.0.1:9001`)

Atalhos disponíveis na raiz via `Makefile`: `make dev`, `make down`, `make logs`, `make validate-infra`, `make test`, `make test-security`, `make migrate`.

---

## 4. Provisionar Servidor Novo

**Pré-requisitos:** Ubuntu/Debian, acesso root via SSH, DNS apontado.

```bash
sudo ./infra/scripts/bootstrap-server.sh \
  --domain sora.app \
  --email admin@sora.app \
  --repo git@github.com:minha-org/sora.git
```

O script é **idempotente** e executa:

1. Instala Docker, Compose plugin, UFW, fail2ban e atualizações automáticas.
2. Configura `/swapfile` de 2 GB (ajustável com `--swap-size`) e tuning de kernel (`vm.swappiness=10`, `vm.overcommit_memory=1`).
3. Cria o usuário de deploy (`sora`) e replica a chave SSH autorizada do root.
4. Firewall liberando **apenas** SSH, 80 e 443.
5. Clona o repositório em `/opt/sora`.
6. **Gera `/opt/sora/.env` com senhas alfanuméricas** (CSPRNG) para:
   - `POSTGRES_PASSWORD` (owner DDL/migrations — 48 chars) e `POSTGRES_APP_PASSWORD` (role `sora_app` com `NOBYPASSRLS` — 48 chars)
   - `REDIS_PASSWORD` (48 chars)
   - `JWT_SECRET_KEY`, `APP_SECRET_KEY` e `ENCRYPTION_KEY` (64 chars cada)
   - `PAYMENT_WEBHOOK_SECRET` (48 chars) e `WHATSAPP_VERIFY_TOKEN` (32 chars)
   - Os valores **não são exibidos** no terminal e o arquivo fica com `chmod 600`.
7. Instala cron diário de backup (03:15) com suporte a alerta de falha via `BACKUP_WEBHOOK_ALERT_URL`.

> O `.env` existente **nunca é sobrescrito**. Para rotacionar segredos, faça manualmente e reinicie os serviços.

### DNS necessário

| Registro | Destino |
| :--- | :--- |
| `api.sora.app` | IP do servidor |
| `app.sora.app` | IP do servidor |
| `*.sora.app` | IP do servidor (opcional, só com overlay wildcard) |

---

## 5. CI/CD (GitHub Actions)

### Secrets — ambiente de desenvolvimento

| Secret | Obrigatório | Descrição |
| :--- | :---: | :--- |
| `DEV_DEPLOY_HOST` | ✅ | IP/host do servidor de desenvolvimento |
| `DEV_DEPLOY_USER` | ✅ | `sora` |
| `DEV_DEPLOY_SSH_KEY` | ✅ | Chave **privada** de deploy |
| `DEV_DEPLOY_PORT` | — | Porta SSH (padrão `22`) |
| `DEV_DEPLOY_PATH` | — | Padrão `/opt/sora` |
| `DEV_DEPLOY_KNOWN_HOSTS` | recomendado | Host key fixada (evita TOFU) |

Obtenha a host key com `ssh-keyscan -H dev.sora.app`.

> Se os secrets `DEV_*` não existirem, o job de deploy é ignorado com aviso — o build continua funcionando.

### Fluxo

| Evento | Ação |
| :--- | :--- |
| PR para `develop`/`main` | Valida os compose files |
| Push em `develop` | Publica `sora-api:develop` e `sora-web:develop` + deploy no servidor de dev |
| Push em `main` | Publica `sora-api:latest` e `sora-web:latest` (sem deploy) |
| Tag `v1.2.3` | Publica imagens imutáveis `v1.2.3` |

Imagens:

```text
ghcr.io/<owner>/sora-api:<develop|latest|vX.Y.Z|sha-xxxx>
ghcr.io/<owner>/sora-web:<develop|latest|vX.Y.Z|sha-xxxx>
```

### Acesso ao GHCR

Se os pacotes forem privados:

- **Servidor de dev (CLI):** PAT com `read:packages` em `/opt/sora/.ghcr-token` (`chmod 600`).
- **Portainer:** Registries → Add registry → `ghcr.io` com usuário e PAT (`read:packages`).

---

## 6. Produção via Portainer (manual)

A produção **não** é atualizada pelo GitHub Actions. O deploy é manual:

1. Faça merge do PR `develop` → `main` (o pipeline executa os testes e publica as imagens `latest`).
2. No Portainer: **Stacks → sora → Pull and redeploy** (habilite *Re-pull image*).
3. Caso a release inclua novas migrations, execute no console do container `api` (ou via SSH):
   `DATABASE_URL="$MIGRATION_DATABASE_URL" alembic upgrade head` (no servidor de `develop`, o `deploy.sh` já executa esse passo automaticamente).

> 🔒 **Segurança do Portainer:** **Nunca** abra as portas `9000`, `8000` ou `9443` do Portainer no firewall público (UFW). Suba o Portainer escutando apenas em loopback (`-p 127.0.0.1:9443:9443`) e acesse via túnel SSH (`ssh -L 9443:127.0.0.1:9443 sora@servidor` → `https://localhost:9443`), ou exponha-o atrás do Traefik com HTTPS e rate limit.

### Configuração da Stack no Portainer

| Campo | Valor |
| :--- | :--- |
| Build method | **Repository** |
| Repository | `https://github.com/<org>/sora` |
| Branch | `main` |
| Compose path | `infra/compose/docker-compose.prod.yml` |
| Environment variables | copiar de `/opt/sora/.env` |

Variáveis obrigatórias na stack: `DOMAIN_BASE`, `ACME_EMAIL`, `API_IMAGE`, `WEB_IMAGE`, `IMAGE_TAG=latest`, `POSTGRES_*`, `REDIS_PASSWORD`, `REDIS_URL`, `DATABASE_URL`, `APP_SECRET_KEY`, `JWT_SECRET_KEY`.

> O compose de produção usa **variáveis de ambiente explícitas** (sem `env_file`), justamente para funcionar com o editor de variáveis do Portainer.

### TLS wildcard no Portainer

Para `{clinica}.sora.app`, use **dois** compose paths na stack (separados por vírgula) ou um `docker-compose.override` no repositório:

```text
infra/compose/docker-compose.prod.yml,infra/compose/docker-compose.tls-dns.yml
```

E adicione `CF_DNS_API_TOKEN` às variáveis da stack.

### Persistência

| Volume | Conteúdo |
| :--- | :--- |
| `sora_pgdata` | Banco PostgreSQL |
| `sora_redisdata` | Redis (AOF) |
| `sora_acmedata` | Certificados Let's Encrypt |

> Recriar a stack no Portainer **não apaga** esses volumes. Não remova volumes sem backup.

---

## 7. Trocar Domínio (Runbook)

O domínio está centralizado em `DOMAIN_BASE`. A troca é simples, mas siga a ordem abaixo para evitar downtime e falha na emissão do certificado.

### 7.1. Antes de trocar

1. **Aponte o DNS novo para o servidor** (antes de qualquer restart):

   | Registro | Destino |
   | :--- | :--- |
   | `<novo-dominio>` | IP do servidor |
   | `app.<novo-dominio>` | IP do servidor |
   | `api.<novo-dominio>` | IP do servidor |
   | `*.<novo-dominio>` | IP do servidor (só se usar subdomínio por clínica) |

2. Confirme a propagação:

   ```bash
   dig +short app.novo-dominio.com
   dig +short api.novo-dominio.com
   ```

3. (Opcional) Mantenha o domínio antigo ativo durante a transição, adicionando um router extra no Traefik. Isso evita downtime até validar o novo.

### 7.2. Troca automatizada (recomendado)

```bash
./infra/scripts/change-domain.sh novo-dominio.com \
  --email admin@novo-dominio.com \
  --email-from noreply@novo-dominio.com
```

O script:

1. Valida o formato do domínio.
2. Resolve `novo-dominio`, `app.` e `api.` e compara com o IP público do servidor (ou com `--expect-ip`).
3. Pede confirmação (`TROCAR`).
4. Faz backup do `.env` (`chmod 600`) e atualiza `DOMAIN_BASE`, `ACME_EMAIL` e `EMAIL_FROM`.
5. Valida o compose e recria Traefik, API e Web.
6. **Restaura o `.env` automaticamente** se qualquer passo falhar.

Flags úteis:

| Flag | Uso |
| :--- | :--- |
| `--expect-ip <ip>` | Valida o DNS contra um IP específico (útil atrás de proxy/CDN) |
| `--skip-dns-check` | Pula a validação (use apenas se souber o que está fazendo) |
| `--no-restart` | Apenas atualiza o `.env` (produção via Portainer) |
| `--yes` | Não pede confirmação |

> **Produção via Portainer:** use `--no-restart` e atualize `DOMAIN_BASE`/`ACME_EMAIL` nas Environment Variables da Stack, depois **Pull and redeploy**.

### 7.3. Troca manual

```bash
# 1. Edite o .env
DOMAIN_BASE=novo-dominio.com
ACME_EMAIL=admin@novo-dominio.com
EMAIL_FROM=noreply@novo-dominio.com

# 2. Recrie os serviços com as novas labels
docker compose --env-file .env -f infra/compose/docker-compose.prod.yml up -d traefik api web
```

### 7.4. Verificação

```bash
curl -I https://app.novo-dominio.com
curl -I https://api.novo-dominio.com
docker compose --env-file .env -f infra/compose/docker-compose.prod.yml logs -f traefik | grep -i acme
```

### 7.5. O que NÃO muda sozinho

- **`NEXT_PUBLIC_*`**: são embutidas no **build** do Next.js. Se o front usa `NEXT_PUBLIC_API_URL`, é necessário **rebuildar a imagem Web** com o novo valor (ou migrar para proxy `/api`/runtime config).
- **Integrações externas**: atualize webhooks do WhatsApp e do gateway Pix, redirect URIs de OAuth/SSO, CORS da API e deep links/configuração do App Mobile.
- **Certificados antigos**: permanecem no volume `sora_acmedata` (inofensivos). Para limpar, pare a stack e remova o volume.
- **E-mail**: se `EMAIL_FROM` não for atualizado, mensagens continuam saindo com o domínio antigo.

### 7.6. Rollback

```bash
# Restaura o .env anterior e recria os serviços
cp -p .env.bak.<timestamp> .env
docker compose --env-file .env -f infra/compose/docker-compose.prod.yml up -d traefik api web
```

> **DNS gratuito + wildcard:** com `sslip.io`/`duckdns.org` o HTTPS por slug funciona, mas **subdomínio por clínica** (`clinica.dominio`) exige certificado wildcard via **DNS Challenge** (ex.: Cloudflare + overlay `docker-compose.tls-dns.yml`).

---

## 8. Deploy Manual (desenvolvimento / CLI)

```bash
cd /opt/sora
IMAGE_TAG=develop SERVICES="api web" ./infra/scripts/deploy.sh
```

O script:

1. Faz `git pull --ff-only` (desative com `AUTO_PULL=0`).
2. Faz login no GHCR (se houver token).
3. Baixa as imagens da tag informada.
4. Sobe os serviços com `--remove-orphans`.
5. Aguarda **healthcheck** (até 4 min); em falha, imprime logs e sai com erro.
6. Remove imagens antigas (> 7 dias).

Com overlay de TLS wildcard:

```bash
COMPOSE_FILES="infra/compose/docker-compose.prod.yml:infra/compose/docker-compose.tls-dns.yml" \
IMAGE_TAG=develop ./infra/scripts/deploy.sh
```

---

## 9. Backup e Restore

### Backup manual

```bash
./infra/scripts/backup-postgres.sh
```

- Gera `backups/postgres/sora-AAAAMMDD-HHMMSS.dump` (formato custom).
- Valida o dump com `pg_restore --list`.
- Retenção de **7 dias** (`RETENTION_DAYS`).
- Opcional: envie para fora do servidor com `rclone`:

```bash
BACKUP_RCLONE_REMOTE="r2:sora-backups/postgres" ./infra/scripts/backup-postgres.sh
```

> **Backup que nunca foi restaurado não é backup.** Teste o restore periodicamente.

### Restore

```bash
./infra/scripts/restore-postgres.sh backups/postgres/sora-20260101-031500.dump
```

Exige digitar `RESTAURAR`. Após o restore, rode `alembic upgrade head`.

> Em produção via Portainer, o backup roda no servidor (cron) ou manualmente via SSH.

---

## 10. Operação e Troubleshooting

```bash
# Status
docker compose --env-file .env -f infra/compose/docker-compose.prod.yml ps

# Logs
docker compose --env-file .env -f infra/compose/docker-compose.prod.yml logs -f --tail=100 api

# Reiniciar um serviço
docker compose --env-file .env -f infra/compose/docker-compose.prod.yml restart api

# Validar configuração
docker compose --env-file .env -f infra/compose/docker-compose.prod.yml config -q
```

| Sintoma | Verificação |
| :--- | :--- |
| Certificado não emitido | DNS aponta para o servidor? Portas 80/443 abertas? Logs do Traefik. |
| `502 Bad Gateway` | Container `api`/`web` saudável? Rota/label correta? |
| `permission denied` no Docker | Usuário precisa reconectar após entrar no grupo `docker`. |
| Wildcard TLS falhando | Overlay aplicado? `CF_DNS_API_TOKEN` válido? |
| Portainer não puxa imagem | Registry `ghcr.io` configurado? Pacote privado exige PAT. |
| Banco não sobe | Permissões do volume `sora_pgdata` e senha nas variáveis da stack. |

---

## 11. Checklist de Segurança

- [ ] Apenas 22, 80 e 443 abertos no firewall.
- [ ] PostgreSQL e Redis sem portas publicadas.
- [ ] `.env` e `.ghcr-token` com `chmod 600`.
- [ ] `acme` em volume nomeado e fora do git.
- [ ] `DEV_DEPLOY_KNOWN_HOSTS` configurado (sem TOFU).
- [ ] Backup diário ativo e restore testado.
- [ ] Imagens com tag imutável (não usar `latest` em rollback).
- [ ] Atualizações de segurança automáticas habilitadas.
- [ ] Portainer com acesso restrito e registry autenticado.
