FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev group)
RUN uv sync --no-dev --no-install-project

# Copy source
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Expose port
EXPOSE 8000

# Entrypoint: run migrations then start server
CMD /app/.venv/bin/alembic upgrade head && /app/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
