#!/usr/bin/env bash
# ==============================================================================
# Sora Studio — Inicialização PostgreSQL 16 (Extensões + Role Zero-Leak RLS)
# ==============================================================================
# Executado automaticamente pelo entrypoint oficial do postgres na criação do
# cluster (/docker-entrypoint-initdb.d/01-init-rls-roles.sh).
#
# Por que criar um usuário separado (sora_app)?
# O superusuário do container ($POSTGRES_USER) possui BYPASSRLS implícito no
# PostgreSQL. Para garantir a Camada 1 do Zero-Leak (Row-Level Security), a API
# deve conectar com um role NOSUPERUSER e NOBYPASSRLS ($POSTGRES_APP_USER),
# enquanto o $POSTGRES_USER é usado apenas para migrations (Alembic DDL).
# ==============================================================================

set -Eeuo pipefail

APP_USER="${POSTGRES_APP_USER:-sora_app}"
APP_PASSWORD="${POSTGRES_APP_PASSWORD:-${POSTGRES_PASSWORD:-}}"

if [ -z "$APP_PASSWORD" ]; then
  echo "ERRO: POSTGRES_APP_PASSWORD (ou POSTGRES_PASSWORD) não definido." >&2
  exit 1
fi

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  -v app_user="$APP_USER" \
  -v app_password="$APP_PASSWORD" \
  -v db_name="$POSTGRES_DB" \
  -v owner_user="$POSTGRES_USER" <<'EOSQL'
-- 1. Extensões obrigatórias do Sora Studio:
--    - uuid-ossp / pgcrypto: geração de UUIDs e criptografia
--    - btree_gist: constraint EXCLUDE USING gist (anti-double-booking na agenda)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- 2. Padroniza timezone interno do banco em UTC
SELECT format('ALTER DATABASE %I SET timezone TO %L', :'db_name', 'UTC') \gexec

-- 3. Cria ou atualiza o role da aplicação com NOBYPASSRLS e NOSUPERUSER
SELECT CASE
  WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user') THEN
    format(
      'ALTER ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS PASSWORD %L',
      :'app_user', :'app_password'
    )
  ELSE
    format(
      'CREATE ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS PASSWORD %L',
      :'app_user', :'app_password'
    )
END \gexec

-- 4. Permissões mínimas necessárias (DML apenas; DDL fica restrito ao owner/migrations)
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'db_name', :'app_user') \gexec
SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'app_user') \gexec
SELECT format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO %I', :'app_user') \gexec
SELECT format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO %I', :'app_user') \gexec

-- 5. Default privileges para todas as tabelas/sequências criadas pelo Alembic ($POSTGRES_USER)
SELECT format(
  'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I',
  :'owner_user', :'app_user'
) \gexec
SELECT format(
  'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO %I',
  :'owner_user', :'app_user'
) \gexec
EOSQL
