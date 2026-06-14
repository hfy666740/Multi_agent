# Makefile — 项目开发常用命令集合
# 技术栈: Make (构建自动化), Docker (容器化), Pytest (测试)
.PHONY: install install-dev dev test test-cov lint format typecheck migrate migrate-new clean build run logs db-shell

install:
	pip install --upgrade pip
	pip install -e .

install-dev: install
	pip install -e ".[dev]"
	pre-commit install

dev:
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest

test-cov:
	pytest --cov=agent --cov=rag --cov=utils --cov=api --cov-report=html

lint:
	ruff check .

format:
	ruff format .
	ruff check . --fix

typecheck:
	mypy agent rag utils api model

migrate:
	alembic upgrade head

migrate-new:
	@read -p "Migration name: " name; alembic revision --autogenerate -m "$$name"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov

build:
	docker-compose build

run:
	docker-compose up -d

logs:
	docker-compose logs -f

db-shell:
	docker exec -it agent-postgres psql -U postgres -d agent_chat
