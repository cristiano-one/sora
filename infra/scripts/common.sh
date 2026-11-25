#!/usr/bin/env bash
# ==============================================================================
# Funções compartilhadas pelos scripts de infraestrutura do Sora
# ==============================================================================
# Uso: source "$(dirname "$0")/common.sh"

set -Eeuo pipefail

SORA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SORA_ENV_FILE="${SORA_ENV_FILE:-$SORA_ROOT/.env}"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2
}

die() {
  log "ERRO: $*"
  exit 1
}

require_root() {
  [ "$(id -u)" -eq 0 ] || die "execute como root (sudo)."
}

require_env_file() {
  [ -f "$SORA_ENV_FILE" ] || die "arquivo .env não encontrado em $SORA_ENV_FILE (rode o bootstrap-server.sh)."
  local perms
  perms="$(stat -c '%a' "$SORA_ENV_FILE")"
  case "$perms" in
    600|400) ;;
    *) log "AVISO: $SORA_ENV_FILE com permissões $perms (recomendado: 600)." ;;
  esac
}

# Monta os argumentos de compose a partir de COMPOSE_FILES (separado por ':').
# Padrão: infra/compose/docker-compose.prod.yml
compose_args() {
  local files="${COMPOSE_FILES:-infra/compose/docker-compose.prod.yml}"
  local parts=() f
  IFS=':' read -r -a parts <<< "$files"
  for f in "${parts[@]}"; do
    [[ "$f" = /* ]] || f="$SORA_ROOT/$f"
    printf '%s\n' -f "$f"
  done
}

compose() {
  local args=()
  while IFS= read -r token; do
    args+=("$token")
  done < <(compose_args)

  docker compose --env-file "$SORA_ENV_FILE" "${args[@]}" "$@"
}
