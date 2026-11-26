import Link from "next/link";

const FEATURES = [
  {
    tag: "Agenda",
    title: "Uma agenda que acompanha o ritmo da sua equipe",
    description:
      "Visão mensal, filtros por profissional, anti-conflito e ações em poucos cliques. Crie, confirme, conclua e reagende sem sair da tela.",
    points: [
      "Calendário com status por cor",
      "Reagendamento e confirmação rápidos",
      "Cada profissional vê apenas a própria agenda",
    ],
  },
  {
    tag: "SORA IA",
    title: "Atendimento no WhatsApp 24 horas por dia",
    description:
      "A SORA IA responde dúvidas, envia o link de agendamento, consulta horários e escala para a equipe quando precisa de aprovação humana.",
    points: [
      "Persona e tom de voz da sua marca",
      "Link mágico sem senha e sem app",
      "Aprovação de exceções em um clique",
    ],
  },
  {
    tag: "Financeiro",
    title: "Caixa, DRE e comissões sem misturar conceitos",
    description:
      "Saiba quanto entrou no caixa, quanto é lucro real por competência e quanto cada profissional recebeu — tudo separado e auditável.",
    points: [
      "Fluxo de caixa e saldo por conta",
      "DRE com custos, taxas e comissões",
      "Folha, adiantamentos e pró-labore",
    ],
  },
  {
    tag: "Prontuário",
    title: "Ficha clínica segura para quem precisa",
    description:
      "Evoluções cifradas, consentimento LGPD, fotos antes/depois e anexos privados com URL temporária. Perfis não clínicos não exibem o prontuário.",
    points: [
      "Notas clínicas cifradas",
      "Anexos com URL de 60 segundos",
      "Perfil de negócio controla os módulos",
    ],
  },
];

const SEGMENTS = [
  {
    icon: "✚",
    title: "Clínicas e estética",
    text: "Prontuário, anamnese, fotos, pacotes e clube de assinatura.",
  },
  {
    icon: "◇",
    title: "Podologia",
    text: "Ficha clínica, evolução do tratamento e recorrência de sessões.",
  },
  {
    icon: "✂",
    title: "Salões",
    text: "Agenda, comissões, pacotes, estoque e recorrência.",
  },
  {
    icon: "◈",
    title: "Barbearias",
    text: "Fluxo rápido, assinaturas, comissões e atendimento no WhatsApp.",
  },
];

const STEPS = [
  {
    number: "01",
    title: "Crie sua conta",
    text: "Escolha o tipo de negócio e comece com a estrutura certa desde o primeiro dia.",
  },
  {
    number: "02",
    title: "Configure sua operação",
    text: "Serviços, equipe, horários, comissões e formas de pagamento em um só lugar.",
  },
  {
    number: "03",
    title: "Atenda e acompanhe",
    text: "Use a agenda, a comanda e a SORA IA enquanto o painel mostra caixa, DRE e clientes.",
  },
];

const FAQ = [
  {
    question: "A Sora serve para clínica, salão e barbearia?",
    answer:
      "Sim. Ao criar a conta você escolhe o perfil do negócio. Prontuário aparece apenas em clínicas, estética e podologia; salões e barbearias mantêm agenda, comissões, estoque e financeiro.",
  },
  {
    question: "O cliente precisa instalar aplicativo?",
    answer:
      "Não. O agendamento acontece por link no WhatsApp, sem senha e sem baixar app. A equipe usa o painel web e o app mobile quando quiser.",
  },
  {
    question: "Como funcionam as comissões?",
    answer:
      "Você define percentual, valor fixo e base de cálculo por profissional. A comissão é apurada sobre atendimentos concluídos e pode ser paga pela folha.",
  },
  {
    question: "Meus dados ficam isolados?",
    answer:
      "Sim. Cada empresa é um tenant isolado por Row-Level Security no PostgreSQL, com RBAC em três níveis e auditoria das ações sensíveis.",
  },
];

export default function LandingPage() {
  return (
    <main className="landing">
      <header className="landing-nav">
        <Link className="landing-brand" href="/">
          <span className="brand-mark">S</span>
          <span>
            <strong>Sora Studio</strong>
            <small>Gestão para beleza e saúde</small>
          </span>
        </Link>
        <nav className="landing-links">
          <a href="#recursos">Recursos</a>
          <a href="#segmentos">Segmentos</a>
          <a href="#como-funciona">Como funciona</a>
          <a href="#planos">Planos</a>
        </nav>
        <div className="landing-nav-actions">
          <Link className="button button-ghost button-small" href="/login">
            Entrar
          </Link>
          <Link className="button button-small" href="/cadastro">
            Começar agora
          </Link>
        </div>
      </header>

      <section className="landing-hero">
        <div className="landing-hero-copy">
          <span className="landing-eyebrow">
            Agenda · Financeiro · WhatsApp · Prontuário
          </span>
          <h1>
            Menos cliques.
            <br />
            Mais atendimentos.
          </h1>
          <p>
            A Sora Studio reúne agenda inteligente, SORA IA no WhatsApp,
            comissões, prontuário e financeiro real em uma plataforma leve —
            feita para clínicas, salões, barbearias e podologia.
          </p>
          <div className="landing-hero-actions">
            <Link className="button landing-button-large" href="/cadastro">
              Criar minha conta
            </Link>
            <a
              className="button button-ghost landing-button-large"
              href="#recursos"
            >
              Ver recursos
            </a>
          </div>
          <div className="landing-trust">
            <span>✓ Agendamento sem app</span>
            <span>✓ WhatsApp nativo</span>
            <span>✓ Dados isolados por empresa</span>
          </div>
        </div>

        <div className="landing-hero-visual" aria-hidden="true">
          <div className="mock-window">
            <div className="mock-topbar">
              <span className="mock-dot" />
              <span className="mock-dot" />
              <span className="mock-dot" />
              <div className="mock-search">Buscar cliente, serviço…</div>
            </div>
            <div className="mock-body">
              <div className="mock-side">
                <div className="mock-brand">S</div>
                <span />
                <span />
                <span />
                <span />
                <span />
              </div>
              <div className="mock-content">
                <div className="mock-greeting">
                  <div>
                    <small>Bom dia, Marina</small>
                    <strong>Hoje você tem 8 atendimentos</strong>
                  </div>
                  <span className="mock-cta">+ Novo</span>
                </div>
                <div className="mock-stats">
                  <div>
                    <small>Agenda</small>
                    <strong>8</strong>
                  </div>
                  <div>
                    <small>Caixa</small>
                    <strong>R$ 1.840</strong>
                  </div>
                  <div>
                    <small>SORA IA</small>
                    <strong>14</strong>
                  </div>
                </div>
                <div className="mock-calendar">
                  <div className="mock-calendar-head">
                    <strong>Novembro</strong>
                    <span>Hoje</span>
                  </div>
                  <div className="mock-week">
                    {["Seg", "Ter", "Qua", "Qui", "Sex"].map((day) => (
                      <small key={day}>{day}</small>
                    ))}
                  </div>
                  <div className="mock-grid">
                    {Array.from({ length: 20 }).map((_, index) => (
                      <span key={index}>
                        {index + 3}
                        {index === 4 ? (
                          <i className="mock-event mock-event-lilac">10h Ana</i>
                        ) : null}
                        {index === 12 ? (
                          <i className="mock-event mock-event-pink">14h Bia</i>
                        ) : null}
                        {index === 17 ? (
                          <i className="mock-event mock-event-blue">16h Léo</i>
                        ) : null}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="landing-floating-card landing-floating-ai">
            <span className="landing-ai-dot">✦</span>
            <div>
              <strong>SORA IA</strong>
              <small>“Tenho horário quinta às 15h?”</small>
            </div>
            <span className="landing-check">✓</span>
          </div>
          <div className="landing-floating-card landing-floating-sale">
            <small>Comanda fechada</small>
            <strong>R$ 180,00</strong>
            <span>Pix confirmado</span>
          </div>
        </div>
      </section>

      <section className="landing-strip">
        <span>Feito para negócios de</span>
        <strong>Estética</strong>
        <strong>Podologia</strong>
        <strong>Salão</strong>
        <strong>Barbearia</strong>
        <strong>Clínica</strong>
      </section>

      <section className="landing-section" id="recursos">
        <div className="landing-section-head">
          <span className="landing-eyebrow">Recursos</span>
          <h2>Tudo o que a operação precisa, sem excesso de cliques</h2>
          <p>
            Cada módulo foi desenhado para reduzir etapas e dar clareza para
            quem atende, gerencia e cuida do caixa.
          </p>
        </div>

        <div className="landing-feature-list">
          {FEATURES.map((feature, index) => (
            <article
              className={`landing-feature ${index % 2 === 1 ? "landing-feature-reverse" : ""}`}
              key={feature.title}
            >
              <div className="landing-feature-copy">
                <span className="landing-tag">{feature.tag}</span>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
                <ul>
                  {feature.points.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>
                <Link
                  className="landing-inline-link"
                  href="/cadastro"
                >
                  Começar com esse módulo →
                </Link>
              </div>
              <div className={`landing-feature-art landing-art-${index}`}>
                {index === 0 ? (
                  <div className="mock-mini-calendar">
                    <div className="mock-mini-head">
                      <strong>Agenda de hoje</strong>
                      <span>8 atendimentos</span>
                    </div>
                    {["09:00 Ana · Corte", "10:30 Bia · Hidratação", "13:00 Léo · Barba"].map(
                      (item, itemIndex) => (
                        <div className="mock-mini-row" key={item}>
                          <span>{itemIndex + 1}</span>
                          <div>
                            <strong>{item}</strong>
                            <small>
                              {itemIndex === 0
                                ? "Confirmado"
                                : itemIndex === 1
                                  ? "Aguardando"
                                  : "Concluído"}
                            </small>
                          </div>
                        </div>
                      ),
                    )}
                  </div>
                ) : null}
                {index === 1 ? (
                  <div className="mock-chat">
                    <div className="mock-chat-head">
                      <span>✦</span> SORA IA · WhatsApp
                    </div>
                    <div className="mock-bubble mock-bubble-in">
                      Oi! Quero agendar limpeza de pele.
                    </div>
                    <div className="mock-bubble mock-bubble-out">
                      Claro! Tenho quinta às 15h ou sexta às 10h. Qual prefere?
                    </div>
                    <div className="mock-bubble mock-bubble-in">
                      Quinta às 15h.
                    </div>
                    <div className="mock-bubble mock-bubble-out">
                      Reservado! Enviei o link de confirmação. ✓
                    </div>
                  </div>
                ) : null}
                {index === 2 ? (
                  <div className="mock-finance">
                    <div className="mock-finance-head">
                      <strong>DRE simplificada</strong>
                      <span>Novembro</span>
                    </div>
                    {[
                      ["Receita bruta", "R$ 28.400", "positive"],
                      ["(-) Custos e taxas", "R$ 4.120", "negative"],
                      ["(-) Comissões", "R$ 5.600", "negative"],
                      ["(=) Lucro líquido", "R$ 18.680", "total"],
                    ].map(([label, value, kind]) => (
                      <div className={`mock-finance-row ${kind}`} key={label}>
                        <span>{label}</span>
                        <strong>{value}</strong>
                      </div>
                    ))}
                  </div>
                ) : null}
                {index === 3 ? (
                  <div className="mock-record">
                    <div className="mock-record-head">
                      <span>MS</span>
                      <div>
                        <strong>Maria Silva</strong>
                        <small>Última evolução · 12/11</small>
                      </div>
                      <span className="mock-lock">🔒</span>
                    </div>
                    <p>
                      Pele sensível. Evitar ácidos por 7 dias. Retorno em 30
                      dias para avaliação.
                    </p>
                    <div className="mock-record-tags">
                      <span>Anamnese</span>
                      <span>Fotos</span>
                      <span>LGPD</span>
                    </div>
                  </div>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section landing-segments" id="segmentos">
        <div className="landing-section-head">
          <span className="landing-eyebrow">Um sistema, vários negócios</span>
          <h2>O menu muda conforme o seu segmento</h2>
          <p>
            Você escolhe o perfil no cadastro. Clínicas e podologia ganham
            prontuário; salões e barbearias ficam com a operação comercial
            enxuta.
          </p>
        </div>
        <div className="landing-segment-grid">
          {SEGMENTS.map((segment) => (
            <article className="landing-segment-card" key={segment.title}>
              <span className="landing-segment-icon">{segment.icon}</span>
              <h3>{segment.title}</h3>
              <p>{segment.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section landing-how" id="como-funciona">
        <div className="landing-section-head">
          <span className="landing-eyebrow">Como funciona</span>
          <h2>Do cadastro ao primeiro atendimento</h2>
        </div>
        <div className="landing-steps">
          {STEPS.map((step) => (
            <article key={step.number}>
              <span>{step.number}</span>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section landing-pricing" id="planos">
        <div className="landing-section-head">
          <span className="landing-eyebrow">Planos</span>
          <h2>Comece com a estrutura que o seu negócio precisa</h2>
          <p>
            Crie sua conta, escolha o perfil e configure sua operação. Os planos
            comerciais podem evoluir conforme a sua equipe cresce.
          </p>
        </div>
        <div className="landing-pricing-grid">
          <article className="landing-price-card">
            <span>Essencial</span>
            <h3>Para começar</h3>
            <p>Agenda, clientes, serviços e link de agendamento.</p>
            <ul>
              <li>Agenda e link mágico</li>
              <li>Cadastro de clientes</li>
              <li>Serviços e pacotes</li>
            </ul>
            <Link className="button button-ghost" href="/cadastro">
              Criar conta
            </Link>
          </article>
          <article className="landing-price-card landing-price-highlight">
            <span className="landing-tag">Mais completo</span>
            <h3>Pro</h3>
            <p>Operação completa com IA, financeiro e comissões.</p>
            <ul>
              <li>Tudo do Essencial</li>
              <li>SORA IA e automações</li>
              <li>Financeiro, DRE e folha</li>
            </ul>
            <Link className="button" href="/cadastro">
              Começar agora
            </Link>
          </article>
          <article className="landing-price-card">
            <span>Rede</span>
            <h3>Para crescer</h3>
            <p>Mais equipes, unidades e governança.</p>
            <ul>
              <li>Tudo do Pro</li>
              <li>Perfis e permissões</li>
              <li>Exportação e auditoria</li>
            </ul>
            <Link className="button button-ghost" href="/cadastro">
              Falar com a equipe
            </Link>
          </article>
        </div>
      </section>

      <section className="landing-section landing-faq">
        <div className="landing-section-head">
          <span className="landing-eyebrow">Dúvidas</span>
          <h2>Perguntas frequentes</h2>
        </div>
        <div className="landing-faq-grid">
          {FAQ.map((item) => (
            <details key={item.question}>
              <summary>{item.question}</summary>
              <p>{item.answer}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="landing-final-cta">
        <span className="landing-eyebrow">Pronto para começar?</span>
        <h2>Menos planilhas. Mais tempo com seus clientes.</h2>
        <p>
          Crie sua conta, escolha o perfil do negócio e comece a organizar a
          operação hoje.
        </p>
        <div className="landing-hero-actions">
          <Link className="button landing-button-large" href="/cadastro">
            Criar minha conta
          </Link>
          <Link
            className="button button-ghost landing-button-large"
            href="/login"
          >
            Já sou cliente
          </Link>
        </div>
      </section>

      <footer className="landing-footer">
        <div>
          <strong>Sora Studio</strong>
          <span>Gestão para beleza e saúde.</span>
        </div>
        <div className="landing-footer-links">
          <Link href="/login">Entrar</Link>
          <Link href="/cadastro">Criar conta</Link>
          <a href="#recursos">Recursos</a>
          <a href="#planos">Planos</a>
        </div>
        <small>© 2026 Sora Studio. Todos os direitos reservados.</small>
      </footer>
    </main>
  );
}
