.PHONY: test-unit test-integration test-e2e test-isolation test-all migrate server

test-unit:
	uv run pytest tests/ -m "not integration" -v

test-integration:
	uv run pytest tests/ -m integration -v

test-e2e:
	uv run pytest tests/e2e/ -v

test-isolation:
	uv run pytest tests/test_isolation.py tests/e2e/test_isolation_suite.py -v

test-all:
	uv run pytest tests/ -v

migrate:
	uv run alembic upgrade head

server:
	uv run uvicorn src.main:app --reload
