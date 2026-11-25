#!/usr/bin/env bash
# ==============================================================================
# Sora — Backup do PostgreSQL
# ==============================================================================
# Gera dump comprimido (formato custom), valida a integridade, aplica retenção
# e dispara alerta via webhook caso ocorra falha.
#
# Uso:
#   ./infra/scripts/backup-postgres.sh
#
# Variáveis:
#   BACKUP_DIR                (padrão: <repo>/backups/postgres)
#   RETENTION_DAYS            (padrão: 7)
#   BACKUP_RCLONE_REMOTE      (opcional) ex.: "r2:sora-backups/postgres"
#   BACKUP_WEBHOOK_ALERT_URL  (opcional) Webhook (Slack/Discord/HTTP) p/ alerta de falha
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

require_env_file
cd "$SORA_ROOT"

BACKUP_DIR="${BACKUP_DIR:-$SORA_ROOT/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
[ "$RETENTION_DAYS" -ge 1 ] 2>/dev/null || die "RETENTION_DAYS inválido."

notify_failure() {
  local exit_code="$?"
  local alert_url="${BACKUP_WEBHOOK_ALERT_URL:-}"
  if [ -z "$alert_url" ] && [ -f "$SORA_ENV_FILE" ]; then
    alert_url="$(grep -E '^BACKUP_WEBHOOK_ALERT_URL=' "$SORA_ENV_FILE" | head -n1 | cut -d'=' -f2- || true)"
  fi
  if [ -n "$alert_url" ] && command -v curl >/dev/null 2>&1; then
    local host_name
    host_name="$(hostname 2>/dev/null || echo 'sora-server')"
    curl -fsSL -X POST -H "Content-Type: application/json" \
      -d "{\"content\":\"❌ [Sora Backup] Falha ao gerar backup do PostgreSQL em ${host_name} (exit ${exit_code}).\",\"text\":\"❌ [Sora Backup] Falha ao gerar backup do PostgreSQL em ${host_name} (exit ${exit_code}).\"}" \
      "$alert_url" >/dev/null 2>&1 || true
  fi
  exit "$exit_code"
}
trap notify_failure ERR

install -d -m 700 "$BACKUP_DIR"

timestamp="$(date '+%Y%m%d-%H%M%S')"
target="$BACKUP_DIR/sora-$timestamp.dump"

log "Gerando backup do PostgreSQL..."
compose exec -T postgres sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "$target.tmp"

mv "$target.tmp" "$target"
chmod 600 "$target"

[ -s "$target" ] || die "backup vazio: $target"

# Valida a integridade do dump
if ! compose exec -T postgres pg_restore --list < "$target" >/dev/null; then
  die "dump inválido (pg_restore --list falhou): $target"
fi

log "Backup válido: $target ($(du -h "$target" | cut -f1))"

# Retenção local
find "$BACKUP_DIR" -type f -name 'sora-*.dump' -mtime "+$RETENTION_DAYS" -delete 2>/dev/null || true

# Cópia opcional para storage remoto
if [ -n "${BACKUP_RCLONE_REMOTE:-}" ]; then
  if command -v rclone >/dev/null 2>&1; then
    log "Enviando backup para $BACKUP_RCLONE_REMOTE..."
    rclone copy "$target" "$BACKUP_RCLONE_REMOTE" || log "AVISO: falha ao enviar para o remoto."
  else
    log "AVISO: BACKUP_RCLONE_REMOTE definido, mas rclone não está instalado."
  fi
fi
