import asyncio
import httpx
import uuid

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Create tenant
        import random
        num = random.randint(1000, 9999)
        resp = await client.post("/tenants", json={"name": f"test tenant {num}"})
        tenant_data = resp.json()
        print("Tenant:", tenant_data)
        api_key = tenant_data.get("raw_api_key")
        headers = {"X-Api-Key": api_key}
        
        # Create client
        resp = await client.post("/clients", json={"name": "test_client", "usage_cap": 100}, headers=headers)
        client_data = resp.json()
        print("Client created:", client_data)
        client_id = client_data.get("id")
        
        # Configure BYOK
        resp = await client.post(f"/clients/{client_id}/byok", json={
            "llm_provider": "openai",
            "llm_model": "gpt-4",
            "llm_api_key": "sk-test"
        }, headers=headers)
        print("BYOK config response:", resp.json())
        
        # Get client
        resp = await client.get(f"/clients/{client_id}", headers=headers)
        print("Get Client:", resp.json())

if __name__ == "__main__":
    asyncio.run(main())
