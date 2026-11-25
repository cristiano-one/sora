#!/usr/bin/env bash
# ==============================================================================
# Sora — Bootstrap de servidor novo (Ubuntu/Debian)
# ==============================================================================
# Instala Docker, swap, firewall, fail2ban, cria usuário de deploy, clona o repo
# e GERA O .env com senhas alfanuméricas fortes (nunca exibidas no terminal).
#
# Uso:
#   sudo ./infra/scripts/bootstrap-server.sh \
#     --domain sora.app \
#     --email admin@sora.app \
#     --repo git@github.com:minha-org/sora.git
#
# Flags:
#   --domain <dominio>     Domínio base (ex.: sora.app)
#   --email <email>        E-mail para Let's Encrypt
#   --repo <url>           URL git do repositório
#   --path <dir>           Diretório de deploy (padrão: /opt/sora)
#   --user <nome>          Usuário de deploy (padrão: sora)
#   --ssh-port <porta>     Porta SSH (padrão: 22)
#   --ghcr-owner <owner>   Owner das imagens no GHCR (padrão: extraído do repo)
#   --swap-size <size>     Tamanho do swapfile (padrão: 2G)
#   --no-swap              Não criar swapfile
#   --no-clone             Não clonar/atualizar o repositório
#   --no-backup-cron       Não instalar o cron de backup diário
#   -h, --help             Ajuda
#
# Idempotente: pode ser reexecutado sem sobrescrever o .env existente.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

DOMAIN="${DOMAIN_BASE:-}"
ACME_EMAIL="${ACME_EMAIL:-}"
REPO_URL="${REPO_URL:-}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/sora}"
DEPLOY_USER="${DEPLOY_USER:-sora}"
SSH_PORT="${SSH_PORT:-22}"
GHCR_OWNER="${GHCR_OWNER:-}"
SWAP_SIZE="${SWAP_SIZE:-2G}"
ENABLE_SWAP=1
DO_CLONE=1
ENABLE_BACKUP_CRON=1

usage() {
  sed -n '2,32p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    --domain) DOMAIN="${2:-}"; shift 2 ;;
    --email) ACME_EMAIL="${2:-}"; shift 2 ;;
    --repo) REPO_URL="${2:-}"; shift 2 ;;
    --path) DEPLOY_PATH="${2:-}"; shift 2 ;;
    --user) DEPLOY_USER="${2:-}"; shift 2 ;;
    --ssh-port) SSH_PORT="${2:-}"; shift 2 ;;
    --ghcr-owner) GHCR_OWNER="${2:-}"; shift 2 ;;
    --swap-size) SWAP_SIZE="${2:-2G}"; shift 2 ;;
    --no-swap) ENABLE_SWAP=0; shift ;;
    --no-clone) DO_CLONE=0; shift ;;
    --no-backup-cron) ENABLE_BACKUP_CRON=0; shift ;;
    -h|--help) usage ;;
    *) die "argumento desconhecido: $1 (use --help)" ;;
  esac
done

require_root

[ -n "$DOMAIN" ] || die "informe --domain (ex.: sora.app)."
[ -n "$ACME_EMAIL" ] || die "informe --email (ex.: admin@sora.app)."

# ------------------------------------------------------------------------------
# Detecção de sistema operacional
# ------------------------------------------------------------------------------
# shellcheck disable=SC1091
. /etc/os-release
case " ${ID:-} ${ID_LIKE:-} " in
  *debian*|*ubuntu*) ;;
  *) die "sistema não suportado: ${PRETTY_NAME:-desconhecido}. Use Ubuntu/Debian." ;;
esac

# ------------------------------------------------------------------------------
# Pacotes básicos
# ------------------------------------------------------------------------------
log "Instalando pacotes básicos..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
  adduser ca-certificates curl gnupg git openssl sudo ufw fail2ban unattended-upgrades

# ------------------------------------------------------------------------------
# Swap e Tuning de Kernel (evita OOM em VPS e otimiza Redis/PostgreSQL)
# ------------------------------------------------------------------------------
if [ "$ENABLE_SWAP" -eq 1 ]; then
  if [ "$(swapon --show | wc -l)" -eq 0 ] && [ ! -f /swapfile ]; then
    log "Criando /swapfile de $SWAP_SIZE..."
    if command -v fallocate >/dev/null 2>&1; then
      fallocate -l "$SWAP_SIZE" /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048 status=none
    else
      dd if=/dev/zero of=/swapfile bs=1M count=2048 status=none
    fi
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
    if ! grep -q '^/swapfile ' /etc/fstab; then
      printf '/swapfile none swap sw 0 0\n' >> /etc/fstab
    fi
  fi
fi

cat > /etc/sysctl.d/99-sora.conf <<'EOF'
vm.swappiness=10
vm.overcommit_memory=1
EOF
sysctl --system >/dev/null 2>&1 || true

# ------------------------------------------------------------------------------
# Usuário de deploy
# ------------------------------------------------------------------------------
if ! id -u "$DEPLOY_USER" >/dev/null 2>&1; then
  log "Criando usuário de deploy: $DEPLOY_USER"
  adduser --disabled-password --gecos "" "$DEPLOY_USER"
fi

# Reaproveita a chave SSH já autorizada para o root (conteúdo não é exibido)
if [ -s /root/.ssh/authorized_keys ] && [ ! -s "/home/$DEPLOY_USER/.ssh/authorized_keys" ]; then
  install -d -m 700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
  install -m 600 -o "$DEPLOY_USER" -g "$DEPLOY_USER" \
    /root/.ssh/authorized_keys "/home/$DEPLOY_USER/.ssh/authorized_keys"
  log "Chave SSH autorizada replicada para $DEPLOY_USER (conteúdo preservado)."
fi

# ------------------------------------------------------------------------------
# Docker (repositório oficial)
# ------------------------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  log "Instalando Docker Engine..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/${ID}/gpg" -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/%s %s stable\n' \
    "$(dpkg --print-architecture)" "$ID" "${VERSION_CODENAME}" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y --no-install-recommends \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

systemctl enable --now docker
usermod -aG docker "$DEPLOY_USER"

# ------------------------------------------------------------------------------
# Firewall (apenas SSH, HTTP e HTTPS)
# ------------------------------------------------------------------------------
log "Configurando UFW (SSH $SSH_PORT, 80 e 443)..."
ufw default deny incoming
ufw default allow outgoing
ufw allow "${SSH_PORT}/tcp" comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable

# ------------------------------------------------------------------------------
# fail2ban e atualizações de segurança automáticas
# ------------------------------------------------------------------------------
systemctl enable --now fail2ban
systemctl enable --now unattended-upgrades

# ------------------------------------------------------------------------------
# Repositório
# ------------------------------------------------------------------------------
install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$DEPLOY_PATH"

if [ "$DO_CLONE" -eq 1 ]; then
  if [ -d "$DEPLOY_PATH/.git" ]; then
    log "Atualizando repositório existente..."
    sudo -u "$DEPLOY_USER" git -C "$DEPLOY_PATH" pull --ff-only || \
      log "AVISO: git pull falhou; mantendo a versão local."
  elif [ -z "$REPO_URL" ]; then
    log "AVISO: --repo não informado; pulando clone."
  elif [ -z "$(ls -A "$DEPLOY_PATH" 2>/dev/null || true)" ]; then
    log "Clonando repositório..."
    sudo -u "$DEPLOY_USER" git clone "$REPO_URL" "$DEPLOY_PATH"
  else
    die "$DEPLOY_PATH existe e não é um repositório git vazio."
  fi
fi

chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_PATH"

# ------------------------------------------------------------------------------
# Geração de segredos (alfanuméricos fortes)
# ------------------------------------------------------------------------------
# Gera N caracteres [A-Za-z0-9] usando CSPRNG do sistema.
gen_alnum() {
  local length="${1:-48}" value=""
  while [ "${#value}" -lt "$length" ]; do
    value+="$(openssl rand -base64 96 | LC_ALL=C tr -dc 'A-Za-z0-9')"
  done
  printf '%s' "${value:0:length}"
}

if [ -n "$GHCR_OWNER" ]; then
  GHCR_OWNER="${GHCR_OWNER,,}"
elif [ -n "$REPO_URL" ]; then
  _tmp="${REPO_URL%.git}"
  _tmp="${_tmp%/*}"
  GHCR_OWNER="${_tmp##*[:/]}"
  GHCR_OWNER="${GHCR_OWNER,,}"
else
  GHCR_OWNER="change-me"
fi

ENV_PATH="$DEPLOY_PATH/.env"

if [ -f "$ENV_PATH" ]; then
  log "AVISO: $ENV_PATH já existe — mantido sem alterações (nenhum segredo foi regenerado)."
else
  log "Gerando $ENV_PATH com senhas alfanuméricas fortes..."
  PG_PASS="$(gen_alnum 48)"
  PG_APP_PASS="$(gen_alnum 48)"
  REDIS_PASS="$(gen_alnum 48)"
  JWT_SECRET="$(gen_alnum 64)"
  APP_SECRET="$(gen_alnum 64)"
  ENC_KEY="$(gen_alnum 64)"
  WEBHOOK_SECRET="$(gen_alnum 48)"
  VERIFY_TOKEN="$(gen_alnum 32)"
  PG_USER="sora"
  PG_APP_USER="sora_app"
  PG_DB="sora"

  umask 077
  ENV_TMP="$(mktemp)"
  cat > "$ENV_TMP" <<EOF
# Gerado automaticamente por bootstrap-server.sh — NUNCA comitar.
# Senhas alfanuméricas geradas com CSPRNG (openssl).

DOMAIN_BASE=$DOMAIN
ACME_EMAIL=$ACME_EMAIL
CF_DNS_API_TOKEN=

API_IMAGE=ghcr.io/$GHCR_OWNER/sora-api
WEB_IMAGE=ghcr.io/$GHCR_OWNER/sora-web
IMAGE_TAG=latest

POSTGRES_DB=$PG_DB
POSTGRES_USER=$PG_USER
POSTGRES_PASSWORD=$PG_PASS
POSTGRES_APP_USER=$PG_APP_USER
POSTGRES_APP_PASSWORD=$PG_APP_PASS
# Conexão runtime do FastAPI: usa role sora_app (NOSUPERUSER + NOBYPASSRLS)
DATABASE_URL=postgresql+asyncpg://$PG_APP_USER:$PG_APP_PASS@postgres:5432/$PG_DB
# Conexão de migrations (Alembic DDL): usa owner sora
MIGRATION_DATABASE_URL=postgresql+asyncpg://$PG_USER:$PG_PASS@postgres:5432/$PG_DB

REDIS_PASSWORD=$REDIS_PASS
REDIS_URL=redis://:$REDIS_PASS@redis:6379/0

APP_NAME=Sora Studio
APP_ENV=production
APP_DEBUG=false
LOG_LEVEL=INFO
TZ=UTC
DEFAULT_TENANT_TIMEZONE=America/Sao_Paulo
APP_SECRET_KEY=$APP_SECRET
ENCRYPTION_KEY=$ENC_KEY
JWT_SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

WHATSAPP_PROVIDER=meta
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_VERIFY_TOKEN=$VERIFY_TOKEN

AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
AI_API_KEY=
WHISPER_PROVIDER=groq
WHISPER_API_KEY=

PAYMENT_PROVIDER=mock
PAYMENT_API_KEY=
PAYMENT_WEBHOOK_SECRET=$WEBHOOK_SECRET

STORAGE_PROVIDER=s3
STORAGE_BUCKET=
STORAGE_REGION=auto
STORAGE_ENDPOINT=
STORAGE_ACCESS_KEY_ID=
STORAGE_SECRET_ACCESS_KEY=
STORAGE_PRESIGNED_URL_TTL_SECONDS=60

SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=noreply@$DOMAIN
SENTRY_DSN=
BACKUP_WEBHOOK_ALERT_URL=
EOF

  install -m 600 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$ENV_TMP" "$ENV_PATH"
  rm -f "$ENV_TMP"
  unset PG_PASS PG_APP_PASS REDIS_PASS JWT_SECRET APP_SECRET ENC_KEY WEBHOOK_SECRET VERIFY_TOKEN
  log "Segredos gravados em $ENV_PATH (chmod 600). Valores não exibidos."
fi

# ------------------------------------------------------------------------------
# Backup diário (cron)
# ------------------------------------------------------------------------------
if [ "$ENABLE_BACKUP_CRON" -eq 1 ]; then
  log "Instalando cron diário de backup (03:15)..."
  cat > /etc/cron.d/sora-backup <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
15 3 * * * $DEPLOY_USER cd $DEPLOY_PATH && ./infra/scripts/backup-postgres.sh >> /var/log/sora-backup.log 2>&1
EOF
  chmod 644 /etc/cron.d/sora-backup
fi

# ------------------------------------------------------------------------------
# Resumo (sem segredos)
# ------------------------------------------------------------------------------
cat <<EOF

============================================================
 Bootstrap concluído
============================================================
 Domínio:        $DOMAIN
 Deploy path:    $DEPLOY_PATH
 Usuário:        $DEPLOY_USER
 Imagens GHCR:   ghcr.io/$GHCR_OWNER/sora-{api,web}
 Env:            $ENV_PATH (chmod 600)

 Próximos passos:
 1. DNS (registros A para o IP deste servidor):
      $DOMAIN
      api.$DOMAIN
      app.$DOMAIN
      *.$DOMAIN   (opcional: subdomínio por clínica)

 2. GHCR (se os pacotes forem privados):
      crie um PAT com read:packages e salve em $DEPLOY_PATH/.ghcr-token
      chmod 600 $DEPLOY_PATH/.ghcr-token

 3. GitHub > Settings > Secrets and variables > Actions (ambiente develop):
      DEV_DEPLOY_HOST, DEV_DEPLOY_USER, DEV_DEPLOY_SSH_KEY,
      DEV_DEPLOY_PORT (opcional), DEV_DEPLOY_PATH (opcional),
      DEV_DEPLOY_KNOWN_HOSTS (recomendado)

 4. Primeiro deploy:
      sudo -u $DEPLOY_USER bash $DEPLOY_PATH/infra/scripts/deploy.sh

 Observação: o usuário $DEPLOY_USER precisa reconectar para usar o Docker
 sem sudo (grupo docker).
============================================================
EOF
