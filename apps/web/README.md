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

## Validação

```bash
pnpm lint && pnpm tsc --noEmit && pnpm test && pnpm build
```
