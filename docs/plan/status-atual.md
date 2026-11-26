# Status atual — Sora Studio

> Atualizado em 26/11/2026. Referência rápida para retomada.

## Web operacional

Concluído:

- login, cadastro, recuperação de senha e convite;
- perfis de negócio e console master;
- agenda em calendário e ações de status;
- clientes, prontuário, LGPD e créditos;
- catálogo, pacotes, estoque e equipe;
- assinaturas e link público;
- financeiro, DRE, folha, dízimo e comissões;
- SORA IA, persona, aprovação e aniversários;
- comanda digital, check-in e NFS-e mock;
- automações/CRM com worker;
- landing de vendas em `/`;
- configurações em submenus.

Pendências comerciais:

- planos e billing SaaS da Sora;
- checkout/trial/inadimplência;
- gateway real;
- NFS-e real;
- WhatsApp Meta real e LLM;
- deploy de produção;
- autoatendimento completo para reagendar/cancelar;
- painel/TV de sala de espera;
- opt-in/out das automações;
- financeiro para ADMIN;
- comanda no mobile.

## Mobile

Concluído:

- login e sessão;
- Início com resumo e check-ins;
- agenda;
- clientes/score/prontuário;
- equipe;
- perfil/comissão.

Pendente:

- comanda;
- check-in pelo app;
- push notifications;
- financeiro/caixa;
- automações;
- build EAS/APK.

## WhatsApp — como testar

### 1. Mock local (gratuito, agora)

Não precisa de Meta.

- `WHATSAPP_PROVIDER=mock` (padrão).
- Use o simulador na central `/sora-ia`: escolha um telefone, envie a mensagem e
  veja a resposta da SORA IA, a conversa e o takeover/legal.
- Alternativa técnica:
  `POST /api/v1/ai/whatsapp/webhook` com `X-Internal-Token`.
- O mock **não envia mensagem real**; ele registra a conversa e devolve a
  resposta no painel.

### 2. Número de teste da Meta (grátis para desenvolvimento)

A Meta oferece um número de teste/sandbox no WhatsApp Cloud API:

- permite testar com poucos destinatários verificados;
- não exige número próprio nem business verification completa;
- serve para validar webhook, envio, templates e conversas reais;
- limites e políticas podem mudar; conferir o painel da Meta.

Configuração:

```env
WHATSAPP_PROVIDER=meta
WHATSAPP_META_TOKEN=...
WHATSAPP_META_PHONE_NUMBER_ID=...
WHATSAPP_VERIFY_TOKEN=...
```

### 3. Produção

Para atender clientes reais:

- portfólio empresarial e verificação;
- WhatsApp Business Account;
- número dedicado;
- token permanente;
- método de pagamento e tarifas por conversa/template;
- templates aprovados para mensagens fora da janela de 24h.

## Como o webhook entra no sistema

```text
WhatsApp/Meta -> POST /api/v1/ai/whatsapp/webhook
              -> resolve tenant pelo slug
              -> normaliza telefone e localiza/cria conversa
              -> SORA IA responde
              -> grava mensagens com RLS
              -> central /sora-ia mostra o histórico
```

O endpoint real exige `X-Internal-Token`; o roteador/WhatsApp deve enviar esse
header. O simulador autenticado usa o mesmo motor sem precisar do token interno.

## Próximo passo recomendado

1. Validar fluxo no simulador mock.
2. Configurar número de teste da Meta com um telefone verificado.
3. Trocar `WHATSAPP_PROVIDER=mock` para `meta` em ambiente controlado.
4. Só depois conectar número de produção e templates.
