# Research Agent

Pluggable Content Generation Agent exposing both a RESTful API and an MCP (Model Context Protocol) server interface.

## Quick Start (Docker Compose)

The easiest way to get started is using Docker Compose.

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd research_agent
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and fill in your API keys and secure password
   ```

3. **Start the application:**
   ```bash
   docker-compose up -d
   ```
   The API will be available at `http://localhost:8000`.

## Environment Variables

See `.env.example` for the full list of configurable environment variables. Key variables include:
- `ENCRYPTION_SECRET_KEY`: Must be at least 32 characters long. Used for encrypting API keys at rest.
- `DATABASE_URL`: Asyncpg connection string for Postgres.
- `GEMINI_API_KEY`: At least one LLM provider key is required (e.g. Gemini or OpenAI).

## Integration Guide

### Via REST (e.g., Museflow)
You can integrate with the Research Agent using standard REST API calls. Be sure to provide the `X-Api-Key` header with your tenant API key.

```bash
curl -X POST http://localhost:8000/generate \
  -H "X-Api-Key: your-tenant-api-key" \
  -H "Content-Type: application/json" \
  -d '{"brief": "Write a short blog post about AI agents", "client_id": "your-client-uuid"}'
```

### Via MCP (Claude Desktop / Cursor)
The application exposes an MCP server interface via SSE at `http://localhost:8000/mcp`.

**Claude Desktop Configuration (`claude_desktop_config.json`):**
```json
{
  "mcpServers": {
    "research-agent": {
      "command": "uv",
      "args": ["run", "python", "-m", "src.main"]
    }
  }
}
```

## API Documentation

For the full REST API documentation, see [docs/api-reference.md](docs/api-reference.md).
Interactive Swagger documentation is available at `http://localhost:8000/docs` when the server is running.
