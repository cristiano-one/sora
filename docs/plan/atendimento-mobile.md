# Atendimento no mobile (painel da secretária)

> Operação do inbox da SORA IA no app, separada das configurações do agente.
> O acesso é controlado pela permissão `can_manage_ai_inbox`.

## Quem acessa

- `OWNER` e `ADMIN`: sempre;
- `COLLABORATOR`: somente se o gestor marcar **Acesso ao atendimento
  WhatsApp (inbox)** em `/equipe` (web) ou no cadastro/edição do usuário.

A permissão é lida do banco em cada requisição, então a revogação bloqueia o
próximo request imediatamente, sem esperar o token expirar.

A permissão dá acesso a:

- lista e histórico de conversas do tenant;
- telefone e nome do cliente;
- takeover, aprovação, resposta humana e encerramento;
- resumo diário da SORA IA;
- check-ins do dia na recepção.

Não dá acesso a:

- conectar/desconectar WhatsApp;
- configurar Groq, persona ou automações;
- financeiro, DRE ou exportação.

## Tela no app

Nova aba **Atendimento** (ícone ✉), visível apenas para quem tem acesso.

### Visão geral

- cards: conversas abertas, em atendimento humano, aprovações pendentes e
  mensagens do dia;
- **Na recepção**: clientes com check-in confirmado, profissional e horário;
- **Conversas**: nome/telefone, última mensagem, status e horário.

### Detalhe da conversa

- histórico de mensagens;
- **Assumir conversa** (takeover);
- **Aprovar exceção** quando `needs_approval`;
- **Encerrar**;
- responder pelo WhatsApp quando a conversa está em modo humano.

O envio usa o mesmo endpoint da central web e o número da própria clínica.

## API

Endpoints operacionais agora aceitam OWNER/ADMIN ou colaborador com a
permissão:

```text
GET  /api/v1/ai/summary
GET  /api/v1/ai/inbox/checkins
GET  /api/v1/ai/conversations
GET  /api/v1/ai/conversations/{id}
POST /api/v1/ai/conversations/{id}/takeover
POST /api/v1/ai/conversations/{id}/approve
POST /api/v1/ai/conversations/{id}/messages
POST /api/v1/ai/conversations/{id}/close
```

Continuam exclusivos de gestores:

```text
POST /api/v1/ai/whatsapp/simulate
GET  /api/v1/ai/birthday-credits
POST /api/v1/ai/birthday-credits/run
GET  /api/v1/whatsapp/connection
```

`/ai/provider/test` continua exclusivo do `OWNER`.

## Segurança

- RLS garante que a conversa é sempre do tenant atual.
- O colaborador com permissão vê todas as conversas operacionais do tenant
  (papel de recepção). Para escopo “somente meus clientes”, será necessária uma
  permissão separada no futuro.
- A permissão é revogável e auditável indiretamente pelo update de usuário.
- O app não armazena a permissão localmente; `/auth/me` é consultado na sessão.

## Limitações atuais

- Sem push notifications; atualização manual por pull-to-refresh.
- Sem envio de áudio/imagem/documento.
- Sem respostas rápidas ou notas internas.
- Sem check-in pelo app (apenas visualização da recepção).
- Sem atribuição de conversa a um colaborador específico.
