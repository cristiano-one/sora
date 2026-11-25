#!/usr/bin/env bash
# ==============================================================================
# Sora — Restore do PostgreSQL
# ==============================================================================
# ATENÇÃO: sobrescreve os dados atuais do banco.
#
# Uso:
#   ./infra/scripts/restore-postgres.sh backups/postgres/sora-20260101-031500.dump
#   ./infra/scripts/restore-postgres.sh <arquivo> --yes
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

require_env_file
cd "$SORA_ROOT"

dump_file="${1:-}"
confirm="${2:-}"

[ -n "$dump_file" ] || die "informe o arquivo de dump."
[ -f "$dump_file" ] || die "arquivo não encontrado: $dump_file"

if [ "$confirm" != "--yes" ]; then
  printf 'Isso substituirá TODOS os dados do banco. Digite "RESTAURAR" para continuar: ' >&2
  read -r answer
  [ "$answer" = "RESTAURAR" ] || die "operação cancelada."
fi

log "Validando dump..."
compose exec -T postgres pg_restore --list < "$dump_file" >/dev/null \
  || die "dump inválido."

log "Restaurando $dump_file ..."
compose exec -T postgres sh -c \
  'exec pg_restore --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < "$dump_file"

log "Restore concluído. Recomenda-se rodar as migrations (alembic upgrade head)."
