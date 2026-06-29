# Common developer tasks. Run `make help` for the list.
.DEFAULT_GOAL := help
.PHONY: help install lint format test cov data run-backend run-frontend up up-prod down clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install dev dependencies (runtime + test/lint toolchain)
	python -m pip install -r requirements-dev.txt

lint: ## Run ruff lint checks
	python -m ruff check .

format: ## Auto-format the code with ruff
	python -m ruff format .

test: ## Run the test suite
	python -m pytest

cov: ## Run tests with a coverage report and gate
	python -m pytest --cov --cov-report=term-missing

data: ## Regenerate the demo dataset (deterministic)
	python scripts/generate_data.py

run-backend: ## Run the FastAPI backend locally
	python -m uvicorn backend.api:app --reload

run-frontend: ## Run the Streamlit frontend locally
	streamlit run frontend/app.py

up: ## Build & start the full stack (with dev hot-reload override)
	docker compose up --build

up-prod: ## Build & start the production-faithful stack (no override)
	docker compose -f docker-compose.yml up --build

down: ## Stop the stack and remove volumes
	docker compose down -v

clean: ## Remove caches and coverage artifacts
	python -c "import shutil,glob,os; [shutil.rmtree(p, ignore_errors=True) for p in glob.glob('**/__pycache__', recursive=True) + ['.pytest_cache', '.ruff_cache', 'htmlcov']]; [os.remove(f) for f in ['.coverage','coverage.xml','junit.xml'] if os.path.exists(f)]"
