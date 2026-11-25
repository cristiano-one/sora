# Imagens de Referência — Design System do Sora

Esta pasta guarda as referências visuais usadas para construir as telas do produto.
**Antes de criar ou alterar qualquer tela, consulte estas imagens.**

| Arquivo | Referência | O que define |
| :--- | :--- | :--- |
| `ref-1-visual-dashboard-cores.jpg` | Estilo "Beautify" | Perfil visual geral: fundo claro suave, cards arredondados, sombras difusas, badges pastéis, gráficos de área, agenda diária ("Plan Today"), wizard de onboarding e a paleta Azul Royal / Índigo como cor padrão. |
| `ref-2-menu-lateral-descritivo.png` | Estilo "Pulse Clinic" | Estrutura obrigatória do menu lateral esquerdo: ícone + texto descritivo, agrupamento por seções em caixa alta e bloco de perfil do usuário (avatar, nome e cargo) no rodapé. |

## Regras derivadas das referências

1. **Tema customizável por clínica:** a cor primária padrão é Índigo (`#4F46E5`), mas deve ser alterável em `Configurações > Aparência` e aplicada via CSS Variables (`--primary`) no Web e `ThemeProvider` no Mobile. Nunca hardcode cores de marca em componentes.
2. **Sidebar descritiva:** não usar barra apenas de ícones. Itens sempre com ícone + label, agrupados por seção e filtrados por RBAC.
3. **Tela Agenda ("Plan Today"):** saudação contextual, KPIs no topo e cartões ricos de agendamento (serviço, cliente, horário, status do sinal Pix).
4. **Consistência Web + Mobile (iOS/Android):** os mesmos tokens de cor, tipografia, raio de borda e espaçamento devem ser compartilhados.

> O detalhamento completo está na **Seção 3.1** de [`../plano-implementacao-mvp-sora.md`](../plano-implementacao-mvp-sora.md).
