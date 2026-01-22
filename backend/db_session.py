from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from urllib.parse import quote_plus
from database import Base
import os
import logging
from dotenv import load_dotenv
from exceptions import DatabaseError

logger = logging.getLogger(__name__)

load_dotenv()
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "fsdha_db")

encoded_password = quote_plus(MYSQL_PASSWORD)

DATABASE_URL = f"mysql+aiomysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"

engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "False").lower() == "true",
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def init_db():
    """
    Initialize the database tables.

    Returns:
        None
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(f"Database tables initialized successfully for database: {MYSQL_DATABASE}")
    except Exception as e:
        raise DatabaseError(f"Failed to initialize database: {str(e)}")



async def close_db():
    """
    Close the database connection pool.

    Returns:
        None
    """
    try:
        await engine.dispose()
        logger.info("Database connection pool closed")
    except Exception as e:
        raise DatabaseError(f"Failed to close database connection: {str(e)}")


async def get_db() -> AsyncSession:
    """
    Get a database session.

    Returns:
        AsyncSession: A database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
            logger.debug("Database session committed successfully")
        except Exception as e:
            logger.warning(f"Database session error, rolling back: {str(e)}")
            await session.rollback()
            raise DatabaseError(f"Database session error: {str(e)}")
        finally:
            await session.close()
            logger.debug("Database session closed")
