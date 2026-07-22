import asyncio
from httpx import AsyncClient, ASGITransport
from src.main import app

async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test 1: missing api key
        response = await client.get("/tenants")
        print("Test 1 status:", response.status_code)
        print("Test 1 json:", response.json())
        
        # Test 2: invalid api key
        response2 = await client.get("/tenants", headers={"X-Api-Key": "invalid"})
        print("Test 2 status:", response2.status_code)
        print("Test 2 json:", response2.json())

if __name__ == "__main__":
    asyncio.run(main())
