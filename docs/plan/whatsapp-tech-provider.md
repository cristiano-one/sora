# WhatsApp real — Tech Provider (Embedded Signup)

> Modelo escolhido: **Tech Provider**. Cada clínica conecta a própria conta
> WhatsApp Business e cadastra o próprio cartão na Meta. A Sora não intermedeia
> custos de mensagem nem concentra um número único, evitando que o bloqueio de
> uma clínica afete as demais.

## O que está implementado

- Embedded Signup v4 no painel `/configuracoes/whatsapp`.
- Troca do `code` por business token no servidor.
- Inscrição do app no WABA (`subscribed_apps`).
- Registro do número na Cloud API com PIN de 6 dígitos (two-step verification).
- Token e PIN cifrados com `ENCRYPTION_KEY`; nunca retornados pela API.
- Webhook oficial `GET/POST /api/v1/whatsapp/webhook`:
  - verificação `hub.challenge`;
  - assinatura `X-Hub-Signature-256` com o App Secret;
  - roteamento por `phone_number_id` via função `SECURITY DEFINER`;
  - idempotência por `message_id` da Meta.
- Envio de respostas e automações com o token da própria clínica.
- RLS na tabela `tenant_whatsapp_accounts` e RBAC:
  - `OWNER` conecta/desconecta;
  - `OWNER` e `ADMIN` visualizam;
  - `COLLABORATOR` não acessa.
- Simulador local em `/sora-ia` continua funcionando sem Meta.

Fluxo:

```text
Cliente WhatsApp
  -> Meta Cloud API
  -> POST /api/v1/whatsapp/webhook (assinado)
  -> resolve tenant pelo phone_number_id
  -> SORA IA grava conversa (RLS)
  -> resposta enviada com o token da clínica
  -> aparece em /sora-ia
```

## 1. Configurar o app na Meta

1. Crie/abra um app em <https://developers.facebook.com/apps>.
2. Adicione o produto **WhatsApp**.
3. Aceite os termos de **Tech Provider** (quando solicitado).
4. Em **App settings > Basic**, copie:
   - **App ID** → `WHATSAPP_APP_ID`
   - **App Secret** → `WHATSAPP_APP_SECRET`
5. Em **Facebook Login for Business > Settings**, habilite:
   - Client OAuth login
   - Web OAuth login
   - Enforce HTTPS
   - Embedded Browser OAuth Login
   - Strict Mode for redirect URIs
   - Login with the JavaScript SDK
6. Ainda em **Facebook Login for Business > Settings**, adicione o domínio
   público usado no teste em **Allowed domains** e **Valid OAuth redirect URIs**.
   Exemplo de túnel: `xxxxx.trycloudflare.com`.
7. Em **Facebook Login for Business > Configurations**, crie uma configuração:
   - use o template **WhatsApp Embedded Signup Configuration With 60
     Expiration Token** ou crie uma configuração v4 com login variation
     **Embedded Signup** e o produto **Cloud API**;
   - copie o **Configuration ID** → `WHATSAPP_CONFIG_ID`.

## 2. Configurar o webhook na Meta

Em **WhatsApp > Configuration**:

- **Callback URL**:
  `https://SEU-DOMINIO-PUBLICO/api/v1/whatsapp/webhook`
- **Verify token**: o mesmo valor de `WHATSAPP_VERIFY_TOKEN`.
- Clique em **Verify and save**.
- Inscreva os campos:
  - `messages` (mensagens e status);
  - `account_update` (exigido no onboarding de Tech Provider).

Sem HTTPS público a Meta não valida o webhook. Para desenvolvimento, use o
túnel abaixo.

## 3. Variáveis de ambiente

No `.env` da API (nunca comite):

```env
WHATSAPP_PROVIDER=meta
WHATSAPP_GRAPH_VERSION=v27.0
WHATSAPP_APP_ID=...
WHATSAPP_APP_SECRET=...
WHATSAPP_CONFIG_ID=...
WHATSAPP_VERIFY_TOKEN=...
```

Para o link mágico de agendamento abrir no celular, ajuste também:

```env
PUBLIC_BOOKING_BASE_URL=https://SEU-DOMINIO-PUBLICO
WEB_BASE_URL=https://SEU-DOMINIO-PUBLICO
```

Reinicie a API depois de alterar.

## 4. Teste local com túnel HTTPS

O web (`:3000`) faz proxy de `/api/v1/*` para a API (`:8010`), então um único
túnel para a porta 3000 resolve Embedded Signup e webhook:

```bash
make whatsapp-tunnel
```

O comando usa o Cloudflare Quick Tunnel e imprime uma URL
`https://xxxxx.trycloudflare.com`.

1. Coloque essa URL em **Allowed domains** e **Valid OAuth redirect URIs** na
   Meta.
2. Use `https://xxxxx.trycloudflare.com/api/v1/whatsapp/webhook` como Callback
   URL.
3. Defina `PUBLIC_BOOKING_BASE_URL` e `WEB_BASE_URL` com a mesma URL.
4. Reinicie a API.
5. Abra `https://xxxxx.trycloudflare.com/configuracoes/whatsapp`.

O Quick Tunnel é temporário: cada execução gera uma URL nova e exige atualizar
a Meta.

## 5. Usar o sandbox da Meta

1. No App Dashboard, abra **WhatsApp > Quickstart > Access Partner Tools**.
2. Clique em **Claim sandbox account**.
3. Entre no Embedded Signup da Sora com o **mesmo desenvolvedor** que reivindicou
   o sandbox.
4. Selecione os ativos do sandbox e conclua.
5. O sandbox permite enviar para até 5 destinatários verificados; ele expira em
   90 dias.
6. Cadastre o cartão da clínica no WhatsApp Manager quando for usar produção.

## 6. Validar uma conversa real

1. Acesse `/configuracoes/whatsapp` como `OWNER`.
2. Defina um PIN de 6 dígitos e clique em **Conectar WhatsApp**.
3. Conclua o fluxo da Meta.
4. Confirme o status **conectado** e o registro na Cloud API.
5. Do seu celular, envie uma mensagem para o número conectado:
   - `Oi, quero agendar um horário`
   - `Quais os preços?`
   - `Meus agendamentos`
6. A resposta da SORA IA deve chegar no WhatsApp.
7. A conversa aparece em `/sora-ia`, com histórico e opção de takeover humano.

A Meta permite resposta livre dentro da janela de atendimento de 24h após a
mensagem do cliente. Mensagens iniciadas pela clínica fora dessa janela exigem
template aprovado (ainda não implementado).

## 7. Diagnóstico rápido

| Sintoma | Verifique |
| :--- | :--- |
| “Integração não configurada” | `WHATSAPP_APP_ID`, `WHATSAPP_CONFIG_ID`, `WHATSAPP_APP_SECRET` e reinício da API |
| Popup não abre | domínio HTTPS em Allowed domains; SDK bloqueado; config ID v4 |
| `502` ao conectar | App Secret, Config ID, code expirado (troque imediatamente), permissões |
| Webhook não valida | `WHATSAPP_VERIFY_TOKEN` igual ao da Meta e URL HTTPS |
| Webhook chega mas não responde | `messages` inscrito, `subscribed_apps` executado, token válido |
| Registro “não confirmado” | número já registrado (pode funcionar) ou PIN inválido; reconecte |
| Mensagem não chega no `/sora-ia` | assinatura recusada, `phone_number_id` desconhecido ou app em modo dev sem o usuário tester |
| Resposta não sai | token expirado/revogado, número sem pagamento ou janela de 24h fechada |

## 8. Produção

Antes de clientes reais:

- verificação do negócio;
- App Review com acesso avançado para `whatsapp_business_management` e
  `whatsapp_business_messaging`;
- app em modo Live;
- política de privacidade e exclusão de dados publicadas;
- templates aprovados para lembretes fora da janela de 24h;
- cartão cadastrado por cada clínica;
- monitoramento de qualidade/limites e rotação de token;
- limite padrão de onboarding: 10 novos WhatsApp accounts por 7 dias (200 após
  verificações).

## 9. Limitações atuais

- Somente mensagens de texto, botões e respostas rápidas são interpretadas.
- Áudio, imagem, documento e localização são ignorados.
- Coexistência com o WhatsApp Business app não está habilitada nesta versão.
- Não há envio de templates pela Sora ainda.
- O webhook processa a mensagem de forma síncrona; para volume alto, migrar para
  fila/worker.
