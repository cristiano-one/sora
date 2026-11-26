# Sora Studio — App Mobile (Expo)

App nativo iOS/Android para colaboradores, administradores e donos da clínica.

## O que tem

- login com JWT + refresh token salvo no **SecureStore**;
- **Agenda** do dia com navegação de data, confirmação, conclusão e
  cancelamento;
- **Início** com resumo do dia, check-ins, comissão, próximos atendimentos e
  atalhos para agenda, clientes e perfil;
- **Agenda** com confirmação, conclusão, cancelamento e status de check-in;
- **Clientes** com busca, telefone mascarado para colaborador, avaliação
  pós-atendimento (+5/−10 no score) e **prontuário**;
- **Prontuário**: evoluções clínicas, consentimento LGPD, fotos pela câmera ou
  galeria, upload privado via pre-signed URL de 60s e exclusão de anexos por
  gestores;
- **Equipe** (gestor/admin) com papéis e comissões;
- **Perfil** com comissão do próprio usuário e logout;
- tema primário da clínica aplicado ao app para gestores.

## Rodar

```bash
cd apps/mobile
pnpm install
pnpm start
```

A API padrão é:

- iOS Simulator: `http://127.0.0.1:8010`
- Android Emulator: `http://10.0.2.2:8010`

Para aparelho físico, use o IP da máquina:

```bash
EXPO_PUBLIC_API_URL=http://192.168.0.10:8010 pnpm start
```

Demo: `demo` · `demo@example.com` · `demo12345`.

## Qualidade

```bash
pnpm lint
pnpm tsc --noEmit
pnpm test
```

> O build nativo (`expo prebuild`/EAS) roda fora deste ambiente; a validação
> aqui é TypeScript + testes + lint.

## Build EAS

O perfil está em `eas.json` (preview interno e production). Requer login e
credenciais da Apple/Google:

```bash
npx eas-cli login
npx eas-cli build --profile preview --platform android
npx eas-cli build --profile production --platform ios
```

`app.json` já define `app.sora.studio` como bundle/package. O projeto EAS
(`extra.eas.projectId`) é criado no primeiro `eas build`/`eas init`.
