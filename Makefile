# Odoo Enterprise Features - Makefile
# =====================================

.PHONY: help build up down restart logs shell test test-unit test-integration test-e2e test-all clean

# Default target
help:
	@echo "Odoo Enterprise Features - Available Commands:"
	@echo "=============================================="
	@echo ""
	@echo "Development:"
	@echo "  build          - Build Docker images"
	@echo "  up             - Start all services"
	@echo "  down           - Stop all services"
	@echo "  restart        - Restart all services"
	@echo "  logs           - Show logs for all services"
	@echo "  shell          - Open shell in Odoo container"
	@echo ""
	@echo "Testing:"
	@echo "  test           - Run all tests"
	@echo "  test-unit      - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-e2e       - Run end-to-end tests only"
	@echo "  test-performance - Run performance tests only"
	@echo "  test-security  - Run security tests only"
	@echo "  test-coverage  - Run tests with coverage report"
	@echo ""
	@echo "Database:"
	@echo "  db-init        - Initialize database"
	@echo "  db-reset       - Reset database"
	@echo "  db-backup      - Backup database"
	@echo "  db-restore     - Restore database"
	@echo ""
	@echo "Utilities:"
	@echo "  clean          - Clean up containers and volumes"
	@echo "  lint           - Run code linting"
	@echo "  format         - Format code"
	@echo "  install        - Install dependencies"
	@echo ""

# Development commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

shell:
	docker-compose exec odoo bash

# Testing commands
test: test-all

test-unit:
	docker-compose -f ops/compose/docker-compose.test.yml run --rm unit_tests

test-integration:
	docker-compose -f ops/compose/docker-compose.test.yml run --rm integration_tests

test-e2e:
	docker-compose -f ops/compose/docker-compose.test.yml run --rm e2e_tests

test-performance:
	docker-compose -f ops/compose/docker-compose.test.yml run --rm performance_tests

test-security:
	docker-compose -f ops/compose/docker-compose.test.yml run --rm security_tests

test-all:
	docker-compose -f ops/compose/docker-compose.test.yml run --rm all_tests

	docker-compose -f ops/compose/docker-compose.test.yml run --rm all_tests
	@echo "Coverage report generated in var/test_results/htmlcov/index.html"

# Database commands
db-init:
	docker-compose exec db psql -U odoo -d odoo -c "CREATE EXTENSION IF NOT EXISTS 'uuid-ossp';"
	docker-compose exec db psql -U odoo -d odoo -c "CREATE EXTENSION IF NOT EXISTS 'hstore';"
	docker-compose exec db psql -U odoo -d odoo -c "CREATE EXTENSION IF NOT EXISTS 'ltree';"
	docker-compose exec db psql -U odoo -d odoo -c "CREATE EXTENSION IF NOT EXISTS 'pg_trgm';"

db-reset:
	docker-compose down -v
	docker-compose up -d db
	sleep 10
	docker-compose up -d

db-backup:
	docker-compose exec db pg_dump -U odoo odoo > backup_$(shell date +%Y%m%d_%H%M%S).sql

db-restore:
	@read -p "Enter backup file name: " file; \
	docker-compose exec -T db psql -U odoo odoo < $$file

# Utility commands
clean:
	docker-compose down -v --remove-orphans
	docker system prune -f
	docker volume prune -f

lint:
	docker-compose exec odoo flake8 addons/ odoo/ tests/
	docker-compose exec odoo black --check addons/ odoo/ tests/
	docker-compose exec odoo isort --check-only addons/ odoo/ tests/

format:
	docker-compose exec odoo black addons/ odoo/ tests/
	docker-compose exec odoo isort addons/ odoo/ tests/

install:
	docker-compose exec odoo pip install -r requirements/requirements.txt

# Development with profiles
dev-up:
	docker-compose --profile dev up -d

dev-down:
	docker-compose --profile dev down

# Monitoring
monitor:
	@echo "Opening monitoring dashboards..."
	@echo "Grafana: http://localhost:3000 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"
	@echo "Flower: http://localhost:5555"
	@echo "Mailhog: http://localhost:8025"
	@echo "PgAdmin: http://localhost:5050 (admin@odoo.com/admin)"
	@echo "Redis Commander: http://localhost:8081"

# Quick start
quick-start: build up db-init
	@echo "Odoo is starting up..."
	@echo "Access Odoo at: http://localhost:8069"
	@echo "Default login: admin/admin"

# Production build
prod-build:
	docker-compose -f docker-compose.yml -f ops/compose/docker-compose.prod.yml build

prod-up:
	docker-compose -f docker-compose.yml -f ops/compose/docker-compose.prod.yml up -d

# Health check
health:
	@echo "Checking service health..."
	@docker-compose ps
	@echo ""
	@echo "Testing Odoo health endpoint..."
	@curl -f http://localhost:8069/web/health || echo "Odoo health check failed"

# Module installation
install-modules:
	docker-compose exec odoo python3 odoo-bin -c /etc/odoo/odoo.conf -i advanced_analytics,advanced_crm,advanced_reports,advanced_inventory,car_rental_fleet -d odoo --stop-after-init

# Module upgrade
upgrade-modules:
	docker-compose exec odoo python3 odoo-bin -c /etc/odoo/odoo.conf -u advanced_analytics,advanced_crm,advanced_reports,advanced_inventory,car_rental_fleet -d odoo --stop-after-init

# Database shell
db-shell:
	docker-compose exec db psql -U odoo -d odoo

# Redis shell
redis-shell:
	docker-compose exec redis redis-cli

# Logs for specific service
logs-odoo:
	docker-compose logs -f odoo

logs-db:
	docker-compose logs -f db

logs-redis:
	docker-compose logs -f redis

# Test specific module
test-module:
	@read -p "Enter module name: " module; \
	docker-compose -f ops/compose/docker-compose.test.yml run --rm all_tests -k $$module

# Performance profiling
profile:
	docker-compose exec odoo python3 -m cProfile -o profile.stats odoo-bin -c /etc/odoo/odoo.conf --stop-after-init
	docker-compose exec odoo python3 -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"

# Memory profiling
memory-profile:
	docker-compose exec odoo python3 -m memory_profiler odoo-bin -c /etc/odoo/odoo.conf --stop-after-init

# Security scan
security-scan:
	docker-compose exec odoo safety check
	docker-compose exec odoo bandit -r addons/ odoo/ tests/

# Documentation
docs:
	docker-compose exec odoo sphinx-build -b html docs/ docs/_build/html

# Backup everything
backup-all:
	@mkdir -p var/backups
	docker-compose exec db pg_dump -U odoo odoo > var/backups/db_$(shell date +%Y%m%d_%H%M%S).sql
	docker-compose exec odoo tar -czf /tmp/odoo_files_$(shell date +%Y%m%d_%H%M%S).tar.gz /opt/odoo/var
	docker cp $$(docker-compose ps -q odoo):/tmp/odoo_files_$(shell date +%Y%m%d_%H%M%S).tar.gz var/backups/

# Restore everything
restore-all:
	@read -p "Enter backup date (YYYYMMDD_HHMMSS): " date; \
	docker-compose exec -T db psql -U odoo odoo < var/backups/db_$$date.sql; \
	docker cp var/backups/odoo_files_$$date.tar.gz $$(docker-compose ps -q odoo):/tmp/; \
	docker-compose exec odoo tar -xzf /tmp/odoo_files_$$date.tar.gz -C /




