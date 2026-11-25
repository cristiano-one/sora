#!/usr/bin/env bash
# ==============================================================================
# Sora — Troca de Domínio com validação de DNS e rollback automático
# ==============================================================================
# Atualiza DOMAIN_BASE (e opcionalmente ACME_EMAIL / EMAIL_FROM) no .env,
# valida os registros DNS, recria Traefik/API/Web e restaura o .env em caso de erro.
#
# Uso:
#   ./infra/scripts/change-domain.sh novo-dominio.com
#   ./infra/scripts/change-domain.sh novo-dominio.com --email admin@novo-dominio.com --yes
#
# Flags:
#   --email <email>      Atualiza ACME_EMAIL
#   --email-from <email> Atualiza EMAIL_FROM
#   --expect-ip <ip>     IP esperado para validar o DNS (padrão: detecta IP público)
#   --skip-dns-check     Pula a validação de DNS
#   --no-restart         Apenas atualiza o .env (não recria containers)
#   --yes                Não pede confirmação
#   -h, --help           Ajuda
#
# Observação: em produção via Portainer, use --no-restart e atualize as
# Environment Variables da Stack no painel do Portainer.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

NEW_DOMAIN=""
NEW_EMAIL=""
NEW_EMAIL_FROM=""
EXPECT_IP=""
SKIP_DNS=0
NO_RESTART=0
ASSUME_YES=0
BACKUP=""
SUCCESS=0

usage() {
  sed -n '2,24p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    --email) NEW_EMAIL="${2:-}"; shift 2 ;;
    --email-from) NEW_EMAIL_FROM="${2:-}"; shift 2 ;;
    --expect-ip) EXPECT_IP="${2:-}"; shift 2 ;;
    --skip-dns-check) SKIP_DNS=1; shift ;;
    --no-restart) NO_RESTART=1; shift ;;
    --yes) ASSUME_YES=1; shift ;;
    -h|--help) usage ;;
    -*) die "flag desconhecida: $1 (use --help)" ;;
    *)
      [ -z "$NEW_DOMAIN" ] || die "informe apenas um domínio."
      NEW_DOMAIN="$1"
      shift
      ;;
  esac
done

require_env_file
cd "$SORA_ROOT"

[ -n "$NEW_DOMAIN" ] || die "informe o novo domínio (ex.: sora.app)."
NEW_DOMAIN="${NEW_DOMAIN,,}"
NEW_DOMAIN="${NEW_DOMAIN#http://}"
NEW_DOMAIN="${NEW_DOMAIN#https://}"
NEW_DOMAIN="${NEW_DOMAIN%%/*}"

[[ "$NEW_DOMAIN" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$ ]] \
  || die "domínio inválido: $NEW_DOMAIN"

resolve_ipv4() {
  local host="$1"
  getent ahostsv4 "$host" 2>/dev/null | awk 'NR==1 {print $1}'
}

# ------------------------------------------------------------------------------
# Validação de DNS (antes de qualquer alteração)
# ------------------------------------------------------------------------------
if [ "$SKIP_DNS" -eq 0 ]; then
  PUBLIC_IP="$EXPECT_IP"
  if [ -z "$PUBLIC_IP" ] && command -v curl >/dev/null 2>&1; then
    PUBLIC_IP="$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)"
  fi

  for host in "$NEW_DOMAIN" "app.$NEW_DOMAIN" "api.$NEW_DOMAIN"; do
    ip="$(resolve_ipv4 "$host")"
    [ -n "$ip" ] || die "DNS ainda não resolve: $host. Aponte o registro A antes de trocar."
    log "DNS OK: $host -> $ip"

    if [ -n "$PUBLIC_IP" ] && [ "$ip" != "$PUBLIC_IP" ]; then
      die "$host resolve para $ip, mas o IP esperado é $PUBLIC_IP. Use --expect-ip ou --skip-dns-check."
    fi
  done

  [ -n "$PUBLIC_IP" ] || log "AVISO: não foi possível detectar o IP público; validação apenas de resolução."
else
  log "AVISO: validação de DNS ignorada (--skip-dns-check)."
fi

# ------------------------------------------------------------------------------
# Confirmação
# ------------------------------------------------------------------------------
if [ "$ASSUME_YES" -ne 1 ]; then
  printf 'Trocar o domínio do ambiente para "%s"? Digite TROCAR para confirmar: ' "$NEW_DOMAIN" >&2
  read -r answer
  [ "$answer" = "TROCAR" ] || die "operação cancelada."
fi

# ------------------------------------------------------------------------------
# Backup + atualização atômica do .env
# ------------------------------------------------------------------------------
BACKUP="${SORA_ENV_FILE}.bak.$(date '+%Y%m%d-%H%M%S')"
cp -p "$SORA_ENV_FILE" "$BACKUP"
chmod 600 "$BACKUP"
log "Backup do .env criado: $BACKUP"

update_env() {
  local key="$1" value="$2" tmp
  tmp="$(mktemp)"
  awk -v k="$key" -v v="$value" '
    BEGIN { found=0 }
    index($0, k"=") == 1 { print k"="v; found=1; next }
    { print }
    END { if (!found) print k"="v }
  ' "$SORA_ENV_FILE" > "$tmp"
  cat "$tmp" > "$SORA_ENV_FILE"
  rm -f "$tmp"
}

update_env "DOMAIN_BASE" "$NEW_DOMAIN"
[ -z "$NEW_EMAIL" ] || update_env "ACME_EMAIL" "$NEW_EMAIL"
[ -z "$NEW_EMAIL_FROM" ] || update_env "EMAIL_FROM" "$NEW_EMAIL_FROM"

[ "$(stat -c '%a' "$SORA_ENV_FILE")" = "600" ] || chmod 600 "$SORA_ENV_FILE"
log "DOMAIN_BASE atualizado para: $NEW_DOMAIN"

if [ "$NO_RESTART" -eq 1 ]; then
  log "Flag --no-restart ativa: nenhum container foi recriado."
  log "No Portainer, atualize DOMAIN_BASE/ACME_EMAIL nas variáveis da Stack e use Pull and redeploy."
  SUCCESS=1
  exit 0
fi

# ------------------------------------------------------------------------------
# Recriação com rollback automático em caso de falha
# ------------------------------------------------------------------------------
rollback() {
  local code=$?
  if [ "$SUCCESS" -ne 1 ] && [ -f "$BACKUP" ]; then
    cp -p "$BACKUP" "$SORA_ENV_FILE"
    log "ERRO: falha ao aplicar o novo domínio. .env restaurado de $BACKUP."
    log "Para reverter os containers manualmente: docker compose up -d traefik api web"
  fi
  exit "$code"
}
trap rollback ERR

log "Validando arquivos compose..."
compose config -q

log "Recriando Traefik, API e Web com o novo domínio..."
compose up -d --remove-orphans traefik api web

SUCCESS=1
trap - ERR

# ------------------------------------------------------------------------------
# Resumo
# ------------------------------------------------------------------------------
cat <<EOF

============================================================
 Domínio atualizado: $NEW_DOMAIN
============================================================
 Acompanhe a emissão dos certificados:
   docker compose logs -f traefik | grep -i acme

 Verifique:
   curl -I https://app.$NEW_DOMAIN
   curl -I https://api.$NEW_DOMAIN

 Não esqueça de atualizar as integrações externas:
   - Webhook do WhatsApp e do gateway Pix
   - Redirect URIs de OAuth/SSO (se houver)
   - CORS da API e deep links do App Mobile
   - NEXT_PUBLIC_* exige NOVO BUILD da imagem Web
============================================================
EOF
