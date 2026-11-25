#!/usr/bin/env bash
# ==============================================================================
# Sora — Deploy no servidor (chamado pelo GitHub Actions ou manualmente)
# ==============================================================================
# Uso:
#   IMAGE_TAG=v1.2.3 SERVICES="api web" ./infra/scripts/deploy.sh
#
# Variáveis:
#   IMAGE_TAG       Tag das imagens (padrão: latest)
#   SERVICES        Serviços a subir (padrão: "api web")
#   COMPOSE_FILES   Arquivos compose separados por ':' (padrão: prod)
#   AUTO_PULL       "1" para git pull antes do deploy (padrão: 1)
#   RUN_MIGRATIONS  "1" para rodar alembic upgrade head antes de subir a API (padrão: 1)
#   GHCR_USER       Usuário do GHCR (padrão: git config ou "github")
#   GHCR_TOKEN      Token read:packages (ou use .ghcr-token no root)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

require_env_file
cd "$SORA_ROOT"

IMAGE_TAG="${IMAGE_TAG:-latest}"
SERVICES="${SERVICES:-api web}"
AUTO_PULL="${AUTO_PULL:-1}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"

read -r -a SERVICE_LIST <<< "$SERVICES"
[ "${#SERVICE_LIST[@]}" -gt 0 ] || die "SERVICES vazio."

# Garante que o Traefik suba junto (não é dependência dos apps)
case " ${SERVICE_LIST[*]} " in
  *" traefik "*) ;;
  *) SERVICE_LIST+=(traefik) ;;
esac

# ------------------------------------------------------------------------------
# Atualiza compose/scripts no servidor
# ------------------------------------------------------------------------------
if [ "$AUTO_PULL" = "1" ] && [ -d "$SORA_ROOT/.git" ]; then
  log "Atualizando código de deploy (git pull --ff-only)..."
  git -C "$SORA_ROOT" pull --ff-only --quiet || \
    log "AVISO: git pull falhou; seguindo com a versão local."
fi

# ------------------------------------------------------------------------------
# Login no GHCR (sem exibir o token)
# ------------------------------------------------------------------------------
if [ -n "${GHCR_TOKEN:-}" ]; then
  GHCR_USER="${GHCR_USER:-github}"
  printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin >/dev/null
  log "Login no GHCR realizado."
elif [ -f "$SORA_ROOT/.ghcr-token" ]; then
  GHCR_USER="${GHCR_USER:-github}"
  docker login ghcr.io -u "$GHCR_USER" --password-stdin < "$SORA_ROOT/.ghcr-token" >/dev/null
  log "Login no GHCR realizado (token local)."
fi

export IMAGE_TAG

# ------------------------------------------------------------------------------
# Pull das imagens
# ------------------------------------------------------------------------------
log "Baixando imagens (tag: $IMAGE_TAG)..."
compose pull "${SERVICE_LIST[@]}"

# ------------------------------------------------------------------------------
# Migrations automáticas (Alembic com MIGRATION_DATABASE_URL / owner role)
# ------------------------------------------------------------------------------
wait_services_healthy() {
  local timeout_sec="$1"
  shift
  local targets=("$@")
  local deadline=$((SECONDS + timeout_sec))
  local ids id status pending

  while [ "$SECONDS" -lt "$deadline" ]; do
    pending=0
    ids="$(compose ps -q "${targets[@]}" 2>/dev/null || true)"
    if [ -z "$ids" ]; then
      pending=1
    else
      for id in $ids; do
        status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id" 2>/dev/null || echo unknown)"
        case "$status" in
          healthy|running) ;;
          *) pending=1 ;;
        esac
      done
    fi
    [ "$pending" -eq 0 ] && return 0
    sleep 3
  done
  return 1
}

if [ "$RUN_MIGRATIONS" = "1" ]; then
  case " ${SERVICE_LIST[*]} " in
    *" api "*)
      log "Garantindo PostgreSQL e Redis ativos antes das migrations..."
      compose up -d postgres redis
      wait_services_healthy 90 postgres redis || die "PostgreSQL/Redis não ficaram saudáveis a tempo."

      log "Executando migrations do banco (Alembic + políticas RLS)..."
      compose run --rm --no-deps api sh -c \
        'if [ -f alembic.ini ]; then DATABASE_URL="${MIGRATION_DATABASE_URL:-$DATABASE_URL}" alembic upgrade head; else echo "alembic.ini ainda não encontrado; pulando migration."; fi'
      ;;
  esac
fi

# ------------------------------------------------------------------------------
# Up + Healthcheck
# ------------------------------------------------------------------------------
log "Subindo serviços: ${SERVICE_LIST[*]}"
compose up -d --remove-orphans "${SERVICE_LIST[@]}"

if wait_services_healthy 240 "${SERVICE_LIST[@]}"; then
  log "Serviços saudáveis. Deploy concluído (tag: $IMAGE_TAG)."
  docker image prune -f --filter "until=168h" >/dev/null 2>&1 || true
else
  log "ERRO: healthcheck não passou no tempo limite."
  compose ps || true
  compose logs --tail=80 "${SERVICE_LIST[@]}" || true
  exit 1
fi
