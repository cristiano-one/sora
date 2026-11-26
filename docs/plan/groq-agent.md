# SORA IA com Groq

> O provedor é configurado **por clínica** em `/configuracoes/agente`.
> A chave é cifrada no banco e nunca retornada pela API.

## Como funciona

O motor determinístico continua sendo a fonte de verdade:

1. classifica a intenção e aplica guardrails;
2. consulta preços, agendamentos, políticas e endereço no banco com RLS;
3. gera a resposta base e o link mágico quando necessário;
4. se a clínica usa Groq, a LLM **apenas reescreve** a resposta base;
5. links e preços são validados; se a LLM inventar algo, a resposta base prevalece.

A LLM não executa ações, não acessa o banco e não recebe `tenant_id`, papel do
usuário ou dados de outras clínicas.

## 1. Criar a chave na Groq

1. Acesse <https://console.groq.com/keys>.
2. Crie uma API key (`gsk_...`).
3. Guarde a chave; ela não é exibida novamente.

## 2. Configurar na Sora

1. Entre como `OWNER`.
2. Abra `/configuracoes/agente`.
3. Em **Provedor de IA**:
   - Provedor: **Groq**
   - Modelo: `llama-3.3-70b-versatile` (ou outro modelo disponível na Groq)
   - Chave da Groq: cole a `gsk_...`
4. Clique em **Salvar agente**.
5. Clique em **Testar conexão**.

O teste retorna o modelo, a latência e uma resposta curta da Groq. A chave não
aparece na resposta nem nos logs.

## 3. Testar sem WhatsApp

Use o simulador em `/sora-ia`:

- `Oi` → saudação;
- `Quais os preços?` → catálogo;
- `Quero agendar` → link mágico;
- `Meus agendamentos` → continua determinístico, por privacidade.

## 4. Quando a Groq é usada

A LLM pode reescrever:

- saudação;
- fallback/conversa geral;
- preços;
- link de agendamento.

Continuam 100% determinísticos:

- guardrails anti-prompt injection;
- “meus agendamentos”;
- aprovação humana;
- transferência para atendente;
- política de cancelamento e endereço (texto exato);
- criação de link, cálculo de preços e qualquer ação.

## 5. Segurança e LGPD

- Chave cifrada com `ENCRYPTION_KEY`; nunca retornada pela API.
- Somente `OWNER` altera provedor/modelo/chave; `ADMIN` só visualiza.
- A mensagem do cliente é enviada à Groq com a chave da própria clínica.
  A clínica deve ter base legal e, em produção, avaliar o DPA da Groq.
- O prompt proíbe revelar regras internas, tokens ou dados de outras clínicas.
- O link mágico de agendamento não é enviado à Groq: a LLM recebe o marcador
  `{{BOOKING_LINK}}` e a Sora substitui pelo link real depois.
- Se a Groq falhar, expirar ou estourar o timeout (3,5s), a resposta
  determinística é usada e o atendimento não para.
- Links e preços gerados pela LLM são validados contra a resposta base.

## 6. Diagnóstico

| Sintoma | Causa provável |
| :--- | :--- |
| `Chave da Groq inválida ou revogada` | chave errada, revogada ou sem permissão |
| `Limite de uso da Groq atingido` | rate limit/cota da conta Groq |
| `Modelo ou requisição inválida` | nome do modelo inexistente ou descontinuado |
| Teste desabilitado | salve a chave antes de testar |
| Resposta continua determinística | provedor em `mock`, chave ausente ou Groq falhou |
| `502` no teste | rede, chave ou modelo; conferir mensagem |

## 7. Produção

- Monitorar latência e fallback.
- Definir limite de gastos na Groq.
- Avaliar modelos e custos por clínica.
- Manter o motor determinístico para ações e dados sensíveis.
- Para volume alto, o webhook deve evoluir para fila/worker; hoje a chamada é
  síncrona para manter o teste simples.
