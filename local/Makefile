# Databrick Local Simulator — convenience targets.
#
# The list of compose files lives once in .env (COMPOSE_FILE), which docker
# compose reads automatically — so every target below just calls `docker compose`
# and they all stay in sync (no copy-pasted -f lists).
#
# Common usage:
#   make init        # download required JARs/tarballs (first time only)
#   make up          # build + start the whole stack
#   make connectors  # register Kafka -> ClickHouse / S3 sink connectors
#   make ps          # show running services
#   make logs        # tail logs for all services
#   make down        # stop the stack and remove volumes
#   make clean       # remove images built for this stack

COMPOSE = docker compose

.DEFAULT_GOAL := help

.PHONY: help init up down restart ps logs connectors config clean docs uc-seed

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

init: ## Download required JARs/tarballs (first time only)
	bash init.sh

up: ## Build and start the whole stack
	$(COMPOSE) up -d --build

down: ## Stop the stack and remove volumes
	$(COMPOSE) down -v

restart: down up ## Restart the whole stack

ps: ## Show running services
	$(COMPOSE) ps

logs: ## Tail logs for all services (use `make logs S=kafka` for one)
	$(COMPOSE) logs -f $(S)

connectors: ## Register Kafka sink connectors (run after `make up`)
	bash init_scripts/setup-connectors.sh

docs: ## Build the training site (../training -> ../training/site), served by home at :8000/training/
	docker run --rm -v "$(CURDIR)/../training":/docs squidfunk/mkdocs-material:9 build
	@echo "training site built -> ../training/site (browse http://localhost:8000/training/ once the stack is up)"

uc-seed: ## Provision the governed 'shopflow' Unity Catalog for the training course (Unit 6)
	bash ../common/uc-cli/seed-governance.sh

config: ## Validate the merged compose configuration
	$(COMPOSE) config -q && echo "compose config OK"

clean: ## Remove images built for this stack
	bash remove-stack.sh
