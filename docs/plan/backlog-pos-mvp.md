# Backlog pós-MVP — Referência Mangomint x operação brasileira

> Complementa [`plano-implementacao-mvp-sora.md`](plano-implementacao-mvp-sora.md).
> Critério: manter apenas o que melhora a operação diária, retenção ou
> competitividade no Brasil, sem copiar o modelo americano de SMS e preço.
>
> **Status:** comanda digital, check-in, motor de automações com templates,
> fiscal mock, vínculo parceiro/MEI e primeira tela Início do mobile já
> implementados. Gateway real, NFS-e real, voz e editor visual seguem pendentes
> de provedor/credenciais.

## 1. O que já temos ou já está no MVP

| Referência | Situação na Sora | Próximo passo |
| :--- | :--- | :--- |
| **Agendamento expresso sem senha/app** | ✅ Link mágico + página pública criam o agendamento sem login | Manter e medir conversão |
| **WhatsApp nativo** | ✅ SORA IA construída em torno do WhatsApp | Plugar Meta Cloud API real |
| **Recepcionista com IA (texto)** | ✅ SORA determinística, persona, aprovação humana e central | Plugar LLM/PydanticAI real |
| **Interface leve e rápida** | ✅ Agenda em calendário, modais e fluxo reduzido de cliques | Criar meta de cliques para comanda |
| **Automação de aniversário** | ✅ Crédito 7 dias antes + worker | Integrar ao motor de automações |
| **Pix** | ✅ Provider mock + adapter | Plugar gateway real |
| **Regime MEI/Completo** | ✅ Cadastro do tenant | Usar no fiscal/NFS-e |
| **Comissões** | ✅ Percentual/fixo, bruto/líquido | Adicionar modelo parceiro/MEI |

## 2. Lacunas que entram no plano de ação

### P0 — Comanda digital rápida

O maior ganho de fluidez do Mangomint vem de fechar o atendimento em poucos
cliques. Hoje a Sora tem agenda, financeiro e comissão, mas ainda não tem uma
comanda operacional única.

**Implementar:**
- abrir comanda a partir do agendamento;
- adicionar serviços, produtos e pacotes;
- aplicar desconto, crédito de aniversário e sinal já pago;
- escolher forma de pagamento (Pix, dinheiro, cartão, boleto);
- calcular comissão, custo, taxas e valor líquido;
- baixar automaticamente no caixa, DRE e comissão;
- imprimir/exportar recibo e permitir estorno auditado.

**Meta de UX:** agendamento → comanda paga em no máximo **3 cliques** no fluxo
comum.

### P0 — Automações de relacionamento e recuperação

O Mangomint tem réguas visuais; no Brasil isso precisa ser **WhatsApp-first**.

**Primeira versão (templates, sem canvas complexo):**
- confirmação imediata do agendamento;
- lembrete 24h e 2h antes;
- pós-atendimento em 24h (agradecimento/avaliação);
- recuperação de cliente sem retorno em 60/90 dias;
- aniversário 7 dias antes (já existe);
- opt-in/opt-out LGPD e pausa por conversa;
- log de envio, falha e conversão.

**Segunda versão:** editor visual de gatilhos, atrasos, condições e metas.

### P1 — Check-in digital e sala de espera

**Implementar:**
- link mágico de check-in ao chegar;
- status `AGUARDANDO` / `CHEGOU` / `EM_ATENDIMENTO` na agenda;
- aviso automático ao profissional quando o cliente chega;
- painel/TV de sala de espera opcional;
- tempo de espera e alerta quando ultrapassar o limite.

### P0 — Pagamentos locais completos

O gateway real é pré-requisito comercial. Além do Pix:

- cartão de crédito à vista e parcelado por link/checkout;
- boleto quando o gateway suportar;
- Pix automático/recorrente para planos;
- conciliação de recebimentos e taxas;
- webhooks idempotentes e assinados;
- estorno/cancelamento auditado;
- integração com maquininhas parceiras em fase posterior (Stone, PagSeguro,
  Cielo via gateway/POS, sem acoplar regra de negócio ao adquirente).

### P0/P1 — Fiscal brasileiro e Lei do Salão-Parceiro

**NFS-e:**
- adapter de provedor fiscal (ex.: Focus NFe, eNotas ou integração municipal);
- configuração por tenant: município, inscrição, código de serviço, alíquota;
- emissão, consulta, cancelamento e download de PDF/XML;
- credenciais cifradas e auditoria.

**Salão-parceiro / MEI:**
- tipo de vínculo por profissional: `EMPLOYEE`, `PARTNER`, `MEI`;
- regra de divisão de comissão sem bitributação;
- separação entre folha e repasse de parceiro;
- relatórios de repasse e documento de prestação de contas;
- alertas e validações contábeis.

### P1 — Autoatendimento do cliente

Já temos agendamento expresso; falta o ciclo completo sem app:

- confirmar, cancelar e reagendar pelo link mágico;
- check-in;
- ver pacotes/cotas e créditos;
- lista de espera;
- preferência de contato e opt-in.

### P2 — Recepcionista por voz

O Mangomint atende ligações; no Brasil o WhatsApp continua prioridade, mas voz
pode entrar depois:

- telefonia + transcrição;
- mesmas tools da SORA com `RunContext` blindado;
- transferência para humano;
- consentimento e gravação;
- fallback quando a confiança for baixa.

## 3. O que não vamos copiar

- **SMS como canal principal:** manter WhatsApp e link mágico.
- **Preço em dólar:** posicionamento em BRL, com planos competitivos.
- **Integração direta com cada maquininha:** começar pelo gateway e avaliar POS
  depois.
- **Canvas de automação complexo já no MVP:** validar templates primeiro.
- **Recepção por voz antes do WhatsApp/LLM reais:** voz é P2.

## 4. Roadmap sugerido pós-MVP

### Fase 6 — Comanda e fluidez operacional
- comanda digital;
- pagamento na comanda;
- check-in/sala de espera;
- atalhos e metas de cliques.

### Fase 7 — Automações e CRM
- templates de confirmação, lembrete, pós-atendimento e recuperação;
- opt-in/out LGPD;
- logs e métricas;
- editor visual depois.

### Fase 8 — Brasil: pagamentos e fiscal
- gateway real (Pix, cartão, boleto);
- NFS-e;
- vínculo parceiro/MEI e repasses;
- conciliação e relatórios.

### Fase 9 — IA avançada
- LLM/PydanticAI real;
- agente por voz;
- automações visuais avançadas;
- integrações POS/maquininhas.

## 5. Regras de aceite transversais

- Toda tabela nova com RLS `FORCE`, policy por tenant e testes cross-tenant.
- Pagamentos/webhooks idempotentes, assinados e auditados.
- Automações com opt-in/opt-out e registro de consentimento.
- Credenciais fiscais/pagamento cifradas, nunca em log.
- Comanda restrita por papel; colaborador vê apenas o que operou.
- Nenhum valor monetário em `float`.
- Ação sensível gera `AuditLog`.

## 6. Métricas para validar a fluidez

- tempo médio para fechar uma comanda;
- cliques por agendamento/comanda;
- taxa de no-show antes/depois dos lembretes;
- conversão do link mágico;
- clientes recuperados por automação;
- tempo de check-in e de espera;
- adesão a Pix/cartão/boleto;
- erros fiscais e reprocessamentos.
