import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app


def test_health():
    async def check_health():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    asyncio.run(check_health())
