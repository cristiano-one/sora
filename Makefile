# ==============================================================================
# Sora Studio — Makefile de Atalhos (Desenvolvimento, Testes e Infraestrutura)
# ==============================================================================

.PHONY: help dev down ps logs validate-infra test test-security lint migrate backup whatsapp-tunnel

help: ## Mostra todos os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

dev: ## Sobe a infraestrutura local (Traefik, PostgreSQL 16 + RLS role, Redis 7, MinIO S3)
	docker compose -f infra/compose/docker-compose.dev.yml up -d

down: ## Para a infraestrutura local
	docker compose -f infra/compose/docker-compose.dev.yml down

ps: ## Lista status dos containers locais
	docker compose -f infra/compose/docker-compose.dev.yml ps

logs: ## Acompanha logs da infraestrutura local
	docker compose -f infra/compose/docker-compose.dev.yml logs -f --tail=100

validate-infra: ## Valida sintaxe dos scripts Bash e de todos os arquivos Docker Compose
	@for f in infra/scripts/*.sh infra/postgres/init/*.sh; do bash -n "$$f" && echo "OK bash: $$f"; done
	@docker compose -f infra/compose/docker-compose.dev.yml config -q && echo "OK compose: dev"
	@sed 's/^CF_DNS_API_TOKEN=.*/CF_DNS_API_TOKEN=ci-dummy/' infra/.env.prod.example > /tmp/sora-make-prod.env
	@docker compose --env-file /tmp/sora-make-prod.env -f infra/compose/docker-compose.prod.yml config -q && echo "OK compose: prod"
	@docker compose --env-file /tmp/sora-make-prod.env -f infra/compose/docker-compose.prod.yml -f infra/compose/docker-compose.tls-dns.yml config -q && echo "OK compose: prod + tls-dns"
	@rm -f /tmp/sora-make-prod.env

lint: ## Executa lint e type-check em todas as camadas existentes
	@if [ -d services/api/app ]; then cd services/api && ruff check . && mypy app; fi
	@if [ -f apps/web/package.json ]; then cd apps/web && pnpm lint && pnpm tsc --noEmit; fi
	@if [ -f apps/mobile/package.json ]; then cd apps/mobile && pnpm lint && pnpm tsc --noEmit; fi

test: ## Executa testes unitários, integração e cobertura em todas as camadas existentes
	@if [ -d services/api/app ]; then cd services/api && pytest -q --cov=app --cov-fail-under=80; fi
	@if [ -f apps/web/package.json ]; then cd apps/web && pnpm test; fi
	@if [ -f apps/mobile/package.json ]; then cd apps/mobile && pnpm test; fi

test-security: ## Executa a suíte de segurança Zero-Leak (RLS, RBAC, Anti-Prompt Injection)
	@if [ -d services/api/app ]; then cd services/api && pytest -q -m security; else echo "services/api/app ainda não inicializado."; fi

migrate: ## Aplica migrations Alembic usando MIGRATION_DATABASE_URL (owner role)
	@if [ -f services/api/alembic.ini ]; then cd services/api && DATABASE_URL="$${MIGRATION_DATABASE_URL:-$$DATABASE_URL}" alembic upgrade head; else echo "services/api/alembic.ini ainda não inicializado."; fi

backup: ## Executa backup manual validado do PostgreSQL
	./infra/scripts/backup-postgres.sh

whatsapp-tunnel: ## Expõe o web (3000) por HTTPS para testar WhatsApp/Embedded Signup
	@echo "Aguardando a URL https://*.trycloudflare.com do Cloudflare Quick Tunnel..."
	@echo "Use a URL em Allowed domains na Meta e como Callback URL:"
	@echo "  https://SUA-URL/api/v1/whatsapp/webhook"
	@docker run --rm --network host cloudflare/cloudflared:latest tunnel --url http://127.0.0.1:3000
