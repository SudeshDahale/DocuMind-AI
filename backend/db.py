from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, String, Float, Integer, Text, ForeignKey
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./documind.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id            = Column(String, primary_key=True)
    email         = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at    = Column(Float, nullable=False)


class APIKey(Base):
    __tablename__ = "api_keys"
    id            = Column(String, primary_key=True)
    user_id       = Column(String, ForeignKey("users.id"), nullable=False)
    encrypted_key = Column(Text, nullable=False)
    created_at    = Column(Float, nullable=False)
    total_calls   = Column(Integer, default=0)
    tokens_used   = Column(Integer, default=0)
    token_limit   = Column(Integer, default=0)   # 0 = unlimited


class Workspace(Base):
    __tablename__ = "workspaces"
    id         = Column(String, primary_key=True)
    user_id    = Column(String, ForeignKey("users.id"), nullable=False)
    name       = Column(String, nullable=False)
    created_at = Column(Float, nullable=False)


class Document(Base):
    __tablename__ = "documents"
    doc_id      = Column(String, primary_key=True)
    user_id     = Column(String, ForeignKey("users.id"), nullable=False)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=True)
    file_name   = Column(String, nullable=False)
    uploaded_at = Column(Float, nullable=False)


class QueryHistory(Base):
    __tablename__ = "query_history"
    id         = Column(String, primary_key=True)
    user_id    = Column(String, ForeignKey("users.id"), nullable=False)
    doc_ids    = Column(Text, nullable=False)
    question   = Column(Text, nullable=False)
    answer     = Column(Text, nullable=False)
    created_at = Column(Float, nullable=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session