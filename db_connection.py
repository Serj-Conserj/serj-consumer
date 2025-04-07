from contextlib import asynccontextmanager
from config import (
    postgres_user,
    postgres_password,
    postgres_host,
    postgres_port,
    postgres_db,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base


def get_database_url():
    return (
        f"postgresql+asyncpg://{postgres_user}:{postgres_password}@"
        f"{postgres_host}:{postgres_port}/{postgres_db}"
    )


engine = create_async_engine(get_database_url(), echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db
