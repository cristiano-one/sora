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

- `/` — visitante novo é levado ao cadastro/onboarding; usuário autenticado
  vai ao dashboard. A landing de apresentação será adicionada depois.
- `/login` — login real (JWT + Redis), recuperação de senha e link de cadastro.
- `/cadastro` — criação de clínica + OWNER, escolha do tipo de negócio e login
  automático.
- `/esqueci-senha` — solicita link de recuperação por e-mail.
- `/redefinir-senha` — define nova senha e revoga sessões antigas.
- `/aceitar-convite` — colaborador convidado define a senha inicial.
- `/dashboard` — agenda, clientes, comissão, SORA IA, caixa e saldo reais.
- `/agenda` — board do dia, disponibilidade, criação, confirmação, conclusão,
  falta, reagendamento e cancelamento (anti-conflito no backend).
- `/clientes` — cadastro, edição, exclusão, score confidencial e bloqueio
  (telefone mascarado para colaboradores).
- `/sistema` — console master do provedor (fora do login do tenant), protegido
  por `SYSTEM_ADMIN_PASSWORD`; lista empresas e define o perfil de negócio.
- `/clientes/[id]` — prontuário (quando o perfil permite), consentimento LGPD,
  anexos privados (abrir, baixar e excluir) e aplicação de créditos.
- `/minha-comissao` — comissão do próprio usuário em qualquer papel.
- `/pagamentos` — sinais Pix pendentes e confirmação manual (`OWNER`/`ADMIN`).
- `/catalogo` — serviços e pacotes com edição, exclusão, duração, buffer,
  preço, custo, sinal e composição.
- `/estoque` — insumos, saldo, mínimo, custo, entradas/saídas/ajustes
  (`OWNER`/`ADMIN`).
- `/equipe` — usuários, edição, exclusão, papéis, comissões e convite por
  e-mail (`OWNER`/`ADMIN`).
- `/assinaturas/assinantes` — assinantes, cotas, cancelamento e exclusão
  (`OWNER`/`ADMIN`).
- `/assinaturas/planos` — planos, edição, ativação e exclusão.
- `/assinaturas/contratar` — contratação manual para um cliente.
- `/assinaturas/novo-plano` — criação de clube/serviço/cotas.
- `/financeiro/fluxo-caixa` — fluxo de caixa realizado (`OWNER`).
- `/financeiro/dre` — DRE por competência (`OWNER`).
- `/financeiro/lancamentos` — lançamentos e baixa de títulos (`OWNER`).
- `/financeiro/contas` — contas/caixas e saldos (`OWNER`).
- `/financeiro/comissoes` — comissões apuradas (`OWNER`).
- `/financeiro/folha` — salários, adiantamentos, pró-labore e repasses, com
  lançamento automático no caixa quando pagos (`OWNER`).
- `/financeiro/dizimo` — provisão, entregas e pendências de dízimo/oferta,
  visível apenas com a flag ativa (`OWNER`).
- `/financeiro/vendas` — valor líquido por atendimento (`OWNER`).
- `/sora-ia` — resumo diário, conversas com tags/filtros, aprovação de
  exceções, takeover humano, respostas e aniversariantes (`OWNER`/`ADMIN`).
- `/configuracoes` — redireciona para Aparência; submenus:
  - `/configuracoes/aparencia` — tema e prévia.
  - `/configuracoes/agenda` — score mínimo e sinal.
  - `/configuracoes/agente` — persona completa da SORA IA.
  - `/configuracoes/financeiro` — dízimo/oferta (`OWNER`).
  - `/configuracoes/automacoes` — crédito de aniversário.
  - `/configuracoes/dados` — perfil do negócio e exportação LGPD.
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

## Perfis de negócio

O administrador do provedor acessa `/sistema` com a senha master
(`SYSTEM_ADMIN_PASSWORD`) e escolhe o segmento de cada empresa:

| Perfil | Prontuário |
| :--- | :---: |
| Clínica médica | ✅ |
| Clínica de estética | ✅ |
| Podologia | ✅ |
| Salão de beleza | ❌ |
| Barbearia | ❌ |
| Multisserviços | ❌ |

O perfil é retornado em `/auth/me` e controla a exibição do prontuário no web e
no mobile. O cliente escolhe o perfil no `/cadastro` no momento da compra; se
não enviar, a API cria como **Multisserviços**. O administrador do sistema pode
alterar depois no console master.

## Validação

```bash
pnpm lint && pnpm tsc --noEmit && pnpm test && pnpm build
```
