COMPOSE := docker compose -f docker-compose.yml --project-directory .

.PHONY: help docker-run-local docker-stop-local docker-stop-local-complete docker-logs-local docker-restart-local

help:
	@echo "docker-run-local             Build and start the local Docker stack"
	@echo "docker-stop-local            Stop the local Docker stack"
	@echo "docker-stop-local-complete   Stop the stack and remove volumes"
	@echo "docker-logs-local            Follow local stack logs"
	@echo "docker-restart-local         Rebuild and restart the local Docker stack"

docker-run-local:
	$(COMPOSE) up --build --pull never -d

docker-stop-local:
	$(COMPOSE) down

docker-stop-local-complete:
	$(COMPOSE) down -v

docker-logs-local:
	$(COMPOSE) logs -f

docker-restart-local: docker-stop-local docker-run-local
