"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { useSettings } from "@/components/settings/settings-context";
import {
  ApiError,
  connectWhatsApp,
  disconnectWhatsApp,
  getWhatsAppConnection,
  type WhatsAppConnection,
} from "@/lib/api";
import { parseEmbeddedSignupMessage, isFacebookOrigin } from "@/lib/whatsapp-signup";

type FacebookLoginResponse = {
  authResponse?: { code?: string } | null;
  status: string;
};

type FacebookSdk = {
  init(options: {
    appId: string;
    autoLogAppEvents: boolean;
    xfbml: boolean;
    version: string;
  }): void;
  login(
    callback: (response: FacebookLoginResponse) => void,
    options: Record<string, unknown>,
  ): void;
};

declare global {
  interface Window {
    FB?: FacebookSdk;
    fbAsyncInit?: () => void;
  }
}

function loadFacebookSdk(appId: string, version: string): Promise<FacebookSdk> {  if (window.FB) {
    window.FB.init({
      appId,
      autoLogAppEvents: true,
      xfbml: true,
      version,
    });
    return Promise.resolve(window.FB);
  }
  return new Promise((resolve, reject) => {
    window.fbAsyncInit = () => {
      const sdk = window.FB;
      if (!sdk) {
        reject(new Error("SDK do Facebook indisponível."));
        return;
      }
      sdk.init({
        appId,
        autoLogAppEvents: true,
        xfbml: true,
        version,
      });
      resolve(sdk);
    };
    document.getElementById("facebook-jssdk")?.remove();
    const script = document.createElement("script");
    script.id = "facebook-jssdk";
    script.src = "https://connect.facebook.net/en_US/sdk.js";
    script.async = true;
    script.defer = true;
    script.crossOrigin = "anonymous";
    script.onerror = () =>
      reject(new Error("Não foi possível carregar o SDK da Meta."));
    document.body.appendChild(script);
  });
}

function formatDateTime(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

const REGISTRATION_LABEL: Record<string, string> = {
  REGISTERED: "registrado",
  FAILED: "não confirmado",
  PENDING: "pendente",
  SKIPPED: "não se aplica",
};

export default function WhatsAppSettingsPage() {
  const { me } = useSettings();
  const [connection, setConnection] = useState<WhatsAppConnection | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pin, setPin] = useState("");
  const [code, setCode] = useState<string | null>(null);
  const [signup, setSignup] = useState<{
    wabaId: string;
    phoneNumberId: string;
  } | null>(null);
  const submitted = useRef(false);

  const isOwner = me?.role === "OWNER";

  const loadConnection = useCallback(async () => {
    setLoading(true);
    try {
      setConnection(await getWhatsAppConnection());
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao carregar a conexão WhatsApp.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadConnection();
  }, [loadConnection]);

  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      if (!isFacebookOrigin(event.origin)) return;
      const parsed = parseEmbeddedSignupMessage(event.data);
      if (!parsed) return;
      if (parsed.event === "CANCEL") {
        submitted.current = false;
        setBusy(false);
        setCode(null);
        setSignup(null);
        setError(
          parsed.currentStep
            ? `Conexão cancelada na etapa ${parsed.currentStep}.`
            : "Conexão com a Meta cancelada.",
        );
        return;
      }
      if (parsed.event === "ERROR") {
        submitted.current = false;
        setBusy(false);
        setCode(null);
        setSignup(null);
        setError(
          parsed.errorMessage
            ? `A Meta recusou: ${parsed.errorMessage}`
            : "A Meta reportou um erro no Embedded Signup.",
        );
        return;
      }
      if (parsed.event !== "FINISH") return;
      if (!parsed.wabaId || !parsed.phoneNumberId) {
        submitted.current = false;
        setBusy(false);
        setError(
          "A Meta não retornou o número. Refira o Embedded Signup no painel da Meta.",
        );
        return;
      }
      setSignup({
        wabaId: parsed.wabaId,
        phoneNumberId: parsed.phoneNumberId,
      });
    }
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  useEffect(() => {
    if (!code || !signup || !pin || submitted.current) return;
    submitted.current = true;
    setBusy(true);
    connectWhatsApp({
      code,
      waba_id: signup.wabaId,
      phone_number_id: signup.phoneNumberId,
      pin,
    })
      .then((data) => {
        setConnection(data);
        setNotice(
          data.registration_status === "REGISTERED"
            ? "WhatsApp conectado e número registrado na Cloud API."
            : "WhatsApp conectado. O registro na Cloud API não foi confirmado; veja o aviso abaixo.",
        );
      })
      .catch((err) => {
        setError(
          err instanceof ApiError
            ? err.message
            : "Falha ao conectar o WhatsApp.",
        );
      })
      .finally(() => {
        setBusy(false);
        setCode(null);
        setSignup(null);
      });
  }, [code, signup, pin]);

  async function handleConnect() {
    if (!connection?.embedded_signup.enabled) return;
    const { app_id, config_id, graph_version } = connection.embedded_signup;
    if (!app_id || !config_id) return;
    if (!/^[0-9]{6}$/.test(pin)) {
      setError("Defina um PIN de 6 dígitos antes de conectar.");
      return;
    }
    setError(null);
    setNotice(null);
    setBusy(true);
    submitted.current = false;
    setCode(null);
    setSignup(null);
    try {
      const sdk = await loadFacebookSdk(app_id, graph_version);
      sdk.login(
        (response) => {
          const authCode = response.authResponse?.code;
          if (!authCode) {
            setBusy(false);
            setError("Login na Meta não concluído.");
            return;
          }
          setCode(authCode);
        },
        {
          config_id,
          response_type: "code",
          override_default_response_type: true,
          extras: {
            setup: {},
          },
        },
      );
    } catch (err) {
      setBusy(false);
      setError(
        err instanceof Error
          ? err.message
          : "Falha ao abrir o login da Meta.",
      );
    }
  }

  async function handleDisconnect() {
    if (
      !window.confirm(
        "Desconectar o WhatsApp? O número deixa de receber mensagens da SORA IA.",
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setConnection(await disconnectWhatsApp());
      setNotice("WhatsApp desconectado.");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao desconectar o WhatsApp.",
      );
    } finally {
      setBusy(false);
    }
  }

  const connected = connection?.status === "CONNECTED";

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>WhatsApp</h1>
          <p>
            Conecte o número da própria clínica pelo Embedded Signup da Meta.
            A cobrança das mensagens fica na conta Meta da clínica, não na Sora.
          </p>
        </div>
        {connection ? (
          <span
            className={`pill ${connected ? "pill-active" : "pill-muted"}`}
          >
            {connected ? "conectado" : "desconectado"}
          </span>
        ) : null}
      </header>

      {error ? <p className="error">{error}</p> : null}
      {notice ? <p className="public-notice">{notice}</p> : null}

      {loading ? (
        <p className="table-empty">Carregando conexão…</p>
      ) : connection ? (
        <>
          {!connection.embedded_signup.enabled ? (
            <section className="panel whatsapp-warning">
              <strong>Integração ainda não configurada no servidor</strong>
              <p>
                O administrador da Sora precisa definir o App ID, o Config ID
                do Embedded Signup e o App Secret da Meta. Enquanto isso, use
                o simulador da SORA IA para validar o fluxo gratuitamente.
              </p>
            </section>
          ) : null}

          <section className="panel">
            <div className="panel-title">
              <div>
                <h2>Conexão da clínica</h2>
                <span className="muted-small">
                  Token armazenado criptografado e nunca exibido.
                </span>
              </div>
            </div>

            {isOwner && connection.embedded_signup.enabled ? (
              <div className="field whatsapp-pin">
                <label htmlFor="whatsapp-pin">
                  PIN de verificação em duas etapas (6 dígitos)
                </label>
                <input
                  id="whatsapp-pin"
                  value={pin}
                  onChange={(event) =>
                    setPin(event.target.value.replace(/\D/g, "").slice(0, 6))
                  }
                  inputMode="numeric"
                  autoComplete="new-password"
                  placeholder="000000"
                  maxLength={6}
                />
                <span className="muted-small">
                  Você define este PIN agora. Ele será usado no registro do
                  número na Cloud API; guarde-o para a verificação em duas
                  etapas.
                </span>
              </div>
            ) : null}

            {connected ? (
              <>
                <div className="whatsapp-number">
                  <div className="whatsapp-badge">WA</div>
                  <div>
                    <strong>{connection.display_phone_number}</strong>
                    <span>{connection.verified_name ?? "WhatsApp Business"}</span>
                  </div>
                  <span className="pill pill-active">conectado</span>
                </div>
                <dl className="whatsapp-facts">
                  <div>
                    <dt>WABA</dt>
                    <dd>{connection.waba_id}</dd>
                  </div>
                  <div>
                    <dt>Phone number ID</dt>
                    <dd>{connection.phone_number_id}</dd>
                  </div>
                  <div>
                    <dt>Qualidade</dt>
                    <dd>{connection.quality_rating ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>Registro Cloud API</dt>
                    <dd>
                      {REGISTRATION_LABEL[connection.registration_status] ??
                        connection.registration_status}
                    </dd>
                  </div>
                  <div>
                    <dt>Conectado em</dt>
                    <dd>{formatDateTime(connection.connected_at)}</dd>
                  </div>
                </dl>
                {connection.registration_status === "FAILED" ? (
                  <div className="whatsapp-warning whatsapp-registration">
                    <strong>Registro na Cloud API não confirmado</strong>
                    <p>
                      {connection.registration_error ??
                        "A Meta recusou o registro do número."}{" "}
                      Se o número já estava registrado, o envio pode funcionar
                      mesmo assim. Caso contrário, reconecte com outro PIN.
                    </p>
                  </div>
                ) : null}
                {isOwner ? (
                  <div className="whatsapp-actions">
                    <button
                      className="button"
                      type="button"
                      onClick={handleConnect}
                      disabled={busy}
                    >
                      {busy ? "Conectando…" : "Reconectar número"}
                    </button>
                    <button
                      className="button button-ghost"
                      type="button"
                      onClick={handleDisconnect}
                      disabled={busy}
                    >
                      Desconectar
                    </button>
                  </div>
                ) : (
                  <p className="muted-small">
                    Somente o proprietário pode reconectar ou desconectar.
                  </p>
                )}
              </>
            ) : (
              <>
                <p>
                  Nenhum número conectado. Ao conectar, a SORA IA passa a
                  responder no WhatsApp real da clínica e os lembretes usam o
                  número da própria clínica.
                </p>
                {isOwner ? (
                  <button
                    className="button"
                    type="button"
                    onClick={handleConnect}
                    disabled={busy || !connection.embedded_signup.enabled}
                  >
                    {busy ? "Abrindo a Meta…" : "Conectar WhatsApp"}
                  </button>
                ) : (
                  <p className="muted-small">
                    Peça ao proprietário da clínica para conectar o número.
                  </p>
                )}
              </>
            )}
          </section>

          <section className="panel whatsapp-steps">
            <div className="panel-title">
              <div>
                <h2>Como funciona</h2>
                <span className="muted-small">
                  Modelo Tech Provider: cada clínica usa a própria conta Meta.
                </span>
              </div>
            </div>
            <ol>
              <li>
                O proprietário clica em <strong>Conectar WhatsApp</strong> e faz
                login na Meta.
              </li>
              <li>
                A Meta pede a criação ou seleção do WhatsApp Business e do
                número da clínica, além do cartão dela para as tarifas.
              </li>
              <li>
                A Sora inscreve o app no WABA, cifra o token e ativa a SORA IA
                nesse número.
              </li>
            </ol>
            <p className="muted-small">
              O número fica isolado por clínica: bloqueios, qualidade e custos
              de uma não afetam as outras. Para testar sem Meta, use o{" "}
              <Link href="/sora-ia">simulador da SORA IA</Link>.
            </p>
          </section>
        </>
      ) : null}
    </div>
  );
}
