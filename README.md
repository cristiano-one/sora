# Sora Studio

> **Plataforma SaaS de gestão para clínicas de estética, salões de beleza, barbearias e podologia** — focada em agilidade extrema via celular/WhatsApp, gestão financeira real (sem misturar caixa com lucro) e arquitetura **Zero-Leak** (isolamento total contra vazamento de dados).

---

## 🎯 Visão Geral

O **Sora Studio** resolve as principais dores de gestores e profissionais da beleza:

- **Dependência do WhatsApp e falta de tempo:** o cliente final agenda por um link leve no WhatsApp (sem baixar app) e o dono/profissional resolve tudo pelo celular.
- **Zero vazamento de dados:** arquitetura multi-tenant com Row-Level Security (RLS), RBAC em 3 níveis e auditoria imutável.
- **Finanças descomplicadas:** separação real entre **Fluxo de Caixa (regime de caixa)**, **DRE (regime de competência)** e **Comissões/Folha**.
- **Agenda sem conflitos:** dupla trava contra *double booking* (Redis Lock + constraint PostgreSQL `EXCLUDE USING gist`).
- **IA real:** **SORA IA** como recepcionista no WhatsApp e copiloto de voz/texto no App.

---

## 🧱 Estrutura do Monorepo

```text
sora/
├── apps/
│   ├── web/                 # Next.js (App Router) + React + TypeScript + Tailwind + shadcn/ui
│   │   ├── (public)/        # Link leve para WhatsApp (SSR rápido, SEO, Agendamento + Pix QR Code)
│   │   └── (dashboard)/     # Painel Web com RBAC: Dono/Gestor, Admin e Barbeiro/Colaborador
│   └── mobile/              # React Native (Expo Router) + TypeScript — iPhone (iOS) e Android
├── services/
│   └── api/                 # Python 3.12 + FastAPI + SQLAlchemy 2.0 (Async) + Pydantic v2
│       ├── app/             # core/ (Auth, RBAC, RLS, Redis), modules/, workers/
│       └── migrations/      # Alembic (com scripts de políticas RLS no PostgreSQL)
├── packages/
│   └── shared/              # Contratos OpenAPI / Tipos TypeScript gerados a partir do FastAPI
├── infra/
│   ├── traefik/             # Configuração Traefik v3, middlewares e certificados TLS
│   ├── compose/             # docker-compose.dev.yml, prod.yml e overlay de TLS wildcard
│   └── scripts/             # bootstrap, deploy, backup e restore
├── docs/
│   ├── plan/                # Plano de arquitetura e implementação do MVP + imagens de referência
│   ├── ideia.md
│   ├── pesquisa_mercado.odt
│   └── matriz_riscos_sistemas_gestao.docx
└── .github/workflows/       # CI/CD (build das imagens + deploy via SSH)
```

---

## 🚀 Stack Tecnológica

| Camada | Tecnologia | Papel |
| :--- | :--- | :--- |
| **Proxy/Edge** | **Traefik v3** | Roteamento de domínios/subdomínios, SSL automático (Let's Encrypt) e rate limiting. |
| **Backend** | **Python 3.12 + FastAPI** | API assíncrona, Pydantic v2, RBAC 3 níveis, motor financeiro `Decimal`. |
| **Banco** | **PostgreSQL 16** | RLS multi-tenant, transações ACID, JSONB (prontuários) e `EXCLUDE USING gist`. |
| **Cache/Lock** | **Redis 7** | Locks distribuídos, holds de Pix, filas (ARQ/Celery) e JWT blacklist. |
| **Web** | **Next.js (App Router)** | Link público ultra-leve + Painel Administrativo RBAC. |
| **Mobile** | **React Native + Expo** | App nativo para **iPhone (iOS)** e **Android**, com câmera, áudio e push. |
| **IA** | **PydanticAI + Whisper** | **SORA IA**: atendente de WhatsApp e copiloto de voz/texto com Zero-Leak via `RunContext`. |

---

## 📋 Documentação Principal

- 📘 **[Plano de Arquitetura e Implementação do MVP](docs/plan/plano-implementacao-mvp-sora.md)** — Arquitetura Zero-Leak, RBAC, regras de negócio, design system, Traefik e roadmap em fases.
- 🤖 **[AGENTS.md](AGENTS.md)** — Regras obrigatórias de testes (incluindo segurança Zero-Leak) e boas práticas para **qualquer modelo de IA** que implementar código neste repositório.
- 🤝 **[CONTRIBUTING.md](CONTRIBUTING.md)** — Setup local, fluxo de PR e validações obrigatórias para pessoas.
- 💡 [Ideias e Dores do Mercado](docs/ideia.md)
- 📊 [Pesquisa de Mercado](docs/pesquisa_mercado.odt)
- ⚠️ [Matriz de Riscos dos Concorrentes](docs/matriz_riscos_sistemas_gestao.docx)

---

## 🌿 Fluxo de Branches e Ambientes

```text
feature/* ──PR──> develop ──PR──> main
                     │              │
                     ▼              ▼
              imagem `develop`   imagem `latest`
              deploy automático  Portainer (manual)
```

| Branch | Pipeline | Ambiente |
| :--- | :--- | :--- |
| `feature/*` | Valida compose no PR | — |
| `develop` | Build `develop` + deploy automático | Desenvolvimento/Homologação |
| `main` | Build `latest` (sem deploy) | Produção via **Portainer** |
| tag `v*.*.*` | Build imutável `v1.2.3` | Rollback / release |

> O repositório usa `main` como branch de produção (equivalente ao "master"). Detalhes em [`infra/README.md`](infra/README.md).

---

## 🛠️ Como Rodar o Ambiente de Desenvolvimento

> **Pré-requisitos:** Docker + Docker Compose, Node.js 20+, Python 3.12+, `uv`/`pip`.

```bash
# 1. Clone o repositório
git clone <repo-url> sora && cd sora

# 2. Configure as variáveis de ambiente
cp .env.example .env   # Preencha as credenciais (nunca comite o .env)

# 3. Suba a infraestrutura local (Traefik, PostgreSQL, Redis)
docker compose -f infra/compose/docker-compose.dev.yml up -d

# 4. Backend (API)
cd services/api
uv sync                  # ou: pip install -r requirements.txt
alembic upgrade head     # Aplica migrations + políticas RLS
uvicorn app.main:app --reload

# 5. Web (Painel + Link Público)
cd apps/web
pnpm install
pnpm dev

# 6. Mobile (Expo — iOS Simulator / Android Emulator)
cd apps/mobile
pnpm install
pnpm expo start
```

Domínios locais esperados (via Traefik): `http://api.sora.localhost:8000`, `http://app.sora.localhost:8000` e `http://{clinica}.sora.localhost:8000`.

> 🚀 **Produção / Deploy:** veja o runbook completo em [`infra/README.md`](infra/README.md) (bootstrap do servidor, geração de segredos, backup e GitHub Actions).

---

## ✅ Diretrizes Obrigatórias de Engenharia e Testes (Para Contribuidores e Agentes de IA)

> **⚠️ REGRA NÃO NEGOCIÁVEL:** Toda implementação, por qualquer modelo de IA ou desenvolvedor, **deve obrigatoriamente passar pela etapa de testes** antes de ser considerada concluída, incluindo **testes de segurança contra vazamento de dados (Zero-Leak)**. Nenhuma feature é entregue sem evidência de testes verdes.

### 1. Testes Obrigatórios em Toda Implementação
Antes de abrir PR ou finalizar uma tarefa, execute e comprove:
- **Testes Unitários:** Regras de negócio, cálculos financeiros (`Decimal`, sem floats), validações Pydantic e permissões.
- **Testes de Integração:** Endpoints FastAPI com banco real (ou testcontainers), migrations Alembic e políticas RLS.
- **Testes de Front-end/E2E:** Fluxos críticos no Next.js (agendamento, sinal Pix, painel) e no App Mobile (Expo).
- **Verificação de Build:** `pnpm build`/`pnpm lint`/`tsc --noEmit` no Web e Mobile; `ruff check` + `mypy` + `pytest` na API.

### 2. Testes de Segurança Zero-Leak (Obrigatórios)
Toda alteração que toque em dados, autenticação, agenda, financeiro, prontuários, IA ou queries deve incluir testes provando:
- **Isolamento Multi-Tenant:** Usuário do tenant A **não** lê/escreve dados do tenant B (mesmo com `id` explícito). Valide RLS ativa no PostgreSQL.
- **RBAC em 3 Níveis:** `COLLABORATOR` não acessa agenda, comissões ou dados de outros profissionais; `ADMIN` não acessa DRE, extrato, dízimo ou exportação de base; apenas `OWNER` acessa esses recursos.
- **Anti-Prompt Injection na SORA IA:** Tente injetar `tenant_id`, `user_id` ou pedir dados de outro cliente/colaborador; o `RunContext` deve impedir e os testes devem falhar ao tentar.
- **Mascaramento de Dados:** Telefone mascarado para `COLLABORATOR`, ausência de score/bloqueio em respostas públicas (`PublicResponse`) e pre-signed URLs com TTL de 60s.
- **Auditoria:** Ações sensíveis geram registro imutável (`who`, `role`, `when`, `ip`, `action`, `resource_id`).
- **Segredos:** Nenhuma credencial, token ou `.env` versionado; logs não expõem PII.

### 3. Boas Práticas de Programação (Padrão do Projeto)
Siga sempre as práticas mais recomendadas da indústria:
- **Clean Code & SOLID:** Funções pequenas, nomes claros, baixo acoplamento e alta coesão.
- **Type Safety:** TypeScript estrito (`strict: true`) no front; Python com type hints + `mypy` + Pydantic no back.
- **Segurança por Padrão:** Validação de entrada, princípio do menor privilégio, OWASP Top 10, queries parametrizadas (sem SQL concatenado).
- **Dinheiro:** Use `Decimal` no Python e `string`/inteiro em centavos no front — **nunca float**.
- **Testes Automatizados:** Todo bug corrigido deve vir com teste de regressão.
- **Migrações Idempotentes:** `alembic upgrade/downgrade` funcionando, com scripts RLS incluídos.
- **Git:** Commits semânticos (`feat:`, `fix:`, `test:`, `docs:`, `chore:`), branches curtas e PRs pequenos.

---

## 📜 Licença

Projeto proprietário — **Sora Studio**. Todos os direitos reservados.
