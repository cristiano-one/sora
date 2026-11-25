# Sora Studio — Web (Next.js)

Slice vertical mínimo do painel: **login real** (JWT + Redis) e **dashboard**
com os dados do usuário autenticado.

## Rodar

```bash
pnpm install
pnpm dev   # http://localhost:3000
```

O Next faz proxy server-side de `/api/v1/*` para `http://127.0.0.1:8010`
(configurável em `API_PROXY_TARGET`). Suba a API com:

```bash
cd services/api
uv run uvicorn app.main:app --reload --port 8010
```

> O README raiz sobe a API na porta `8000`. Para usar essa porta, rode
> `API_PROXY_TARGET=http://127.0.0.1:8000 pnpm dev` (ou ajuste o `.env.local`).

## Demo local

| Campo | Valor |
| :--- | :--- |
| Clínica (slug) | `demo` |
| E-mail | `demo@example.com` |
| Senha | `demo12345` |

## Telas

- `/login` — login real (JWT + Redis).
- `/dashboard` — visão geral com sidebar, perfil e atalhos de gestão.
- `/agenda` — board do dia, disponibilidade em tempo real, criação e
  cancelamento de agendamentos (anti-conflito no backend).
- `/clientes` — cadastro, score confidencial e bloqueio (telefone mascarado
  para colaboradores).
- `/catalogo` — serviços, duração, buffer, preço, custo e sinal.
- `/equipe` — usuários, papéis e comissões (`OWNER`/`ADMIN`).
- `/assinaturas` — planos, cotas, contratação e cancelamento (`OWNER`/`ADMIN`).
- `/configuracoes` — score mínimo, sinal, tema e nome do agente
  (`OWNER`/`ADMIN`).
- `/public/[slug]?t=<token>` — página pública do link mágico (sem login):
  serviços, profissionais, horários livres, planos de assinatura, cotas e
  pagamento Pix (mock).

### Testar o link público (demo)

```bash
# 1) Gere o link (endpoint interno; token padrão de dev)
curl -X POST http://127.0.0.1:8010/api/v1/public/demo/magic-link \
  -H 'Content-Type: application/json' \
  -H 'X-Internal-Token: dev-internal-token' \
  -d '{"phone":"(11) 91234-5678"}'

# 2) Abra a URL retornada no navegador (http://localhost:3000/public/demo?t=...)
```

O token expira em **20 min**. Na página você pode:

- agendar um horário e pagar o sinal pelo **Pix mock** (QR + copia-e-cola);
- assinar o clube da clínica e ativar o plano com o mesmo Pix simulado;
- acompanhar as cotas restantes e agendar usando o plano (tag `Assinante`).

O cliente bloqueado recebe horários vazios e uma mensagem genérica, sem revelar
score/bloqueio.

## Validação

```bash
pnpm lint && pnpm tsc --noEmit && pnpm test && pnpm build
```
