from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


from app.main import app
from app.core.database import get_db, Base

TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5433/clinical_health_test_db"
)


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Cria tabelas uma vez por sessão de testes e as dropa ao final."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    """
    Cada teste recebe sua própria sessão dentro de uma transação que é
    revertida ao fim — banco limpo para o próximo teste sem truncar tabelas.
    """
    conn = await engine.connect()
    trans = await conn.begin()
    session = AsyncSession(bind=conn, expire_on_commit=False)
    yield session
    await session.close()
    await trans.rollback()
    await conn.close()

@pytest_asyncio.fixture()
async def client(db_session):
    """Cliente HTTP que substitui get_db pela sessão de teste."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    )as ac:
        yield ac
    app.dependency_overrides.clear()
