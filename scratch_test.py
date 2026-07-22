import asyncio
from httpx import AsyncClient, ASGITransport
from src.main import app

async def main():
    @app.get("/test-unhandled-error-tmp")
    async def tmp_route():
        raise RuntimeError("Deliberate unhandled exception for testing")
        
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            resp = await client.get("/test-unhandled-error-tmp")
            print("Response:", resp.status_code, resp.json())
        except Exception as e:
            print("Exception raised:", type(e), str(e))

if __name__ == "__main__":
    asyncio.run(main())
