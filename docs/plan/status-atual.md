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
- WhatsApp Tech Provider/Embedded Signup por clínica;
- agente SORA IA com Groq por clínica (chave cifrada e teste de conexão);
- landing de vendas em `/`;
- configurações em submenus.

Pendências comerciais:

- planos e billing SaaS da Sora;
- checkout/trial/inadimplência;
- gateway real;
- NFS-e real;
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

### 2. WhatsApp real por clínica (Tech Provider)

Implementado em `/configuracoes/whatsapp`:

- Embedded Signup v4;
- troca do code por business token;
- inscrição no WABA;
- registro do número com PIN de 6 dígitos;
- token e PIN cifrados;
- webhook oficial assinado e idempotente;
- envio com as credenciais da própria clínica.

A Meta cobra as mensagens na conta de cada clínica. O passo a passo completo,
incluindo sandbox e túnel HTTPS, está em
[`whatsapp-tech-provider.md`](whatsapp-tech-provider.md).

## Agente com Groq

A clínica pode cadastrar a própria chave Groq em `/configuracoes/agente`.
A chave é cifrada, nunca retornada e só o `OWNER` altera. A LLM reescreve
saudações, fallback, preços e link de agendamento; links e preços são validados
e todo o resto continua determinístico. Guia:
[`groq-agent.md`](groq-agent.md).

### 3. Produção

Para atender clientes reais:

- portfólio empresarial e verificação;
- App Review com acesso avançado;
- app em modo Live;
- número dedicado e cartão na conta Meta da clínica;
- templates aprovados para mensagens fora da janela de 24h;
- monitoramento de qualidade e limites.

## Como o webhook entra no sistema

```text
WhatsApp/Meta -> POST /api/v1/whatsapp/webhook (X-Hub-Signature-256)
              -> resolve tenant pelo phone_number_id
              -> normaliza telefone e localiza/cria conversa
              -> SORA IA responde com o token da clínica
              -> grava mensagens com RLS e idempotência
              -> central /sora-ia mostra o histórico
```

O webhook oficial é público, mas só aceita payload com assinatura válida do App
Secret. O endpoint interno antigo (`/api/v1/ai/whatsapp/webhook`) continua
disponível atrás de `X-Internal-Token` para roteadores próprios e simulador.

## Próximo passo recomendado

1. Validar fluxo no simulador mock.
2. Criar o app Meta/Tech Provider e configurar Embedded Signup v4.
3. Subir um túnel HTTPS e cadastrar o webhook.
4. Conectar o sandbox em `/configuracoes/whatsapp`.
5. Enviar uma mensagem real e validar a resposta da SORA IA.
6. Só depois conectar número de produção e templates.
