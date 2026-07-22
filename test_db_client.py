import asyncio
from src.db.session import engine, async_session_maker
from src.repositories import client_repo, tenant_repo
from src.schemas.client import ClientCreate, ClientResponse
from src.services.byok import configure_byok

async def main():
    async with async_session_maker() as session:
        # Create a mock tenant
        from src.models.tenant import Tenant
        tenant = Tenant(name="Test Tenant Direct")
        session.add(tenant)
        await session.flush()
        
        # Create a client
        client_in = ClientCreate(name="Test Client Direct", usage_cap=100)
        client = await client_repo.create_client(session, client_in, tenant.id)
        print("Before BYOK:", ClientResponse.model_validate(client).model_dump())
        
        # Configure BYOK
        client = configure_byok(client, "openai", "gpt-4", "sk-test")
        await session.flush()
        await session.refresh(client)
        print("After BYOK:", ClientResponse.model_validate(client).model_dump())
        
        # Refetch
        refetched = await client_repo.get_client_by_id(session, client.id, tenant.id)
        print("Refetched:", ClientResponse.model_validate(refetched).model_dump())
        
        await session.rollback()

if __name__ == "__main__":
    asyncio.run(main())
