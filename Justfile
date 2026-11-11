# Directories with Python code
SOURCE_DIR := "src"
TESTS_DIR := "tests"

# Default command: list available commands
default:
    @just --list

# Environment variables file
set dotenv-filename := ".env"

# Run all checks: linters and formatting validation
lint: ruff-check

# --- Dependency Management ---

# Update project dependencies
[group('dependencies')]
update:
    uv sync --upgrade

# Sync project dependencies
[group('dependencies')]
sync:
    uv sync

# --- Linters and Formatting ---

# Automatically format code
[group('linters')]
ruff-format:
    python -m ruff check --fix --unsafe-fixes {{ SOURCE_DIR }} {{ TESTS_DIR }}
    python -m ruff format {{ SOURCE_DIR }} {{ TESTS_DIR }}

# Lint code using Ruff
[group('linters')]
ruff-check:
    python -m ruff check {{ SOURCE_DIR }} {{ TESTS_DIR }}
    python -m ruff format --check {{ SOURCE_DIR }} {{ TESTS_DIR }}

# --- Tests ---

# Run the test suite; database tests are skipped when Postgres is not running
[group('tests')]
test:
    uv run pytest -q

# Run the test suite with a coverage report
[group('tests')]
test-cov:
    uv run pytest --cov=src --cov-report=term-missing

# --- Database ---

# Apply all migrations
[group('database')]
migrate:
    uv run alembic upgrade head

# Generate a migration from the models, e.g. just makemigration "add floor to rooms"
[group('database')]
makemigration message:
    uv run alembic revision --autogenerate -m "{{ message }}"

# Roll back the last migration
[group('database')]
downgrade:
    uv run alembic downgrade -1

# Show the SQL of pending migrations without touching the database
[group('database')]
migrate-sql:
    uv run alembic upgrade head --sql

# --- Application ---

# Start the API and the frontend on APP_PORT
[group('app')]
run:
    uv run python -m src

# Create the first administrator, or promote an existing user
[group('app')]
create-admin email password="" name="":
    uv run python -m src.scripts.create_admin --email {{ quote(email) }} \
        {{ if password != "" { "--password " + quote(password) } else { "" } }} \
        {{ if name != "" { "--name " + quote(name) } else { "" } }}

# Fill an empty database with one office, a few rooms and some equipment
[group('app')]
seed:
    uv run python -m src.scripts.seed_demo

# --- Building ---

# Start Postgres and Redis only, for running the app from the host
[group('building')]
deps-up:
    docker compose -f docker-compose.dev.yml up -d

# Stop the dependency containers
[group('building')]
deps-down:
    docker compose -f docker-compose.dev.yml down

# Build and run everything in Docker
[group('building')]
build-local:
    docker compose -f docker-compose.local.yml up -d --build
