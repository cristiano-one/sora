# Contribuindo com o Sora Studio

Obrigado pelo interesse! Este guia resume o fluxo de contribuição. **Leia também o [`AGENTS.md`](AGENTS.md)** — as regras de testes e segurança valem para humanos e para agentes de IA.

---

## 1. Pré-requisitos

- Docker + Docker Compose
- Node.js 20+ e `pnpm`
- Python 3.12+ e `uv` (ou `pip`)
- Conta Expo/EAS (para builds mobile iOS/Android)

---

## 2. Setup Local

```bash
git clone <repo-url> sora && cd sora
cp .env.example .env          # preencha as variáveis locais

docker compose up -d traefik postgres redis

# Backend
cd services/api && uv sync && alembic upgrade head && uvicorn app.main:app --reload

# Web
cd apps/web && pnpm install && pnpm dev

# Mobile
cd apps/mobile && pnpm install && pnpm expo start
```

---

## 3. Fluxo de Contribuição

```text
feature/* ──PR──> develop ──PR──> main
```

| Branch | Papel |
| :--- | :--- |
| `feature/*`, `fix/*`, `security/*` | Trabalho diário |
| `develop` | Integração — PRs são validados aqui primeiro |
| `main` | Produção — recebe apenas merge de `develop` |

1. Crie uma branch a partir de `develop`: `feat/`, `fix/`, `security/`, `docs/`.
2. Implemente com testes (unitários + integração + segurança Zero-Leak quando aplicável).
3. Rode a validação local completa (veja abaixo).
4. Abra o PR **para `develop`** usando o template e preencha as evidências de teste.
5. Aguarde review — PRs sem evidência de testes serão devolvidos.
6. Após validado em `develop`, abra o PR `develop` → `main`.
7. A produção é atualizada **manualmente pelo Portainer** (Pull and redeploy). O pipeline de `main` apenas publica a imagem `latest`.

> O repositório usa `main` como branch de produção (equivalente ao "master").

**Configuração recomendada no GitHub:**
- `develop` como **default branch** (PRs novos apontam para ela).
- Proteger `main`: sem push direto, exigir PR vindo de `develop` e checks verdes.
- Proteger `develop`: exigir PR e checks verdes.

---

## 4. Validação Antes do PR

```bash
# Backend
cd services/api
ruff check . && mypy app && pytest -q --cov=app --cov-fail-under=80 && bandit -r app -q

# Web
cd apps/web
pnpm lint && pnpm tsc --noEmit && pnpm test && pnpm build

# Mobile
cd apps/mobile
pnpm lint && pnpm tsc --noEmit && pnpm test
```

> **Regra:** nenhum PR é aprovado com testes vermelhos ou sem testes para a mudança proposta.

---

## 5. Padrões

- **Commits:** semânticos (`feat:`, `fix:`, `test:`, `docs:`, `security:`, `refactor:`, `chore:`).
- **TypeScript:** `strict: true`, sem `any` injustificado.
- **Python:** type hints, `mypy`, `ruff`, Pydantic v2.
- **Dinheiro:** `Decimal` (backend) e centavos/string (frontend). Nunca `float`.
- **Segurança:** siga o princípio do menor privilégio e o OWASP Top 10.
- **Nunca comite** segredos, `.env`, builds ou certificados.

---

## 6. Segurança

Encontrou uma vulnerabilidade? **Não abra issue pública.** Entre em contato com os mantenedores de forma privada.
