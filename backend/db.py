import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime, func, DECIMAL, Float, Integer, Column
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+asyncmy://chatuser:chatpass@127.0.0.1:3306/groceryshopperai")

class Base(DeclarativeBase):
    pass

class GroceryItem(Base):
    __tablename__ = "grocery_items"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    sub_category: Mapped[str] = mapped_column(String(120), index=True)
    price: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2))
    rating_value: Mapped[float] = mapped_column(Float, nullable=True)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    preferred_llm_model: Mapped[str] = mapped_column(String(50), default="tinyllama")
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    messages = relationship("Message", back_populates="user")
    room_members = relationship("RoomMember", back_populates="user")

class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    messages = relationship("Message", back_populates="room")
    members = relationship("RoomMember", back_populates="room")

class RoomMember(Base):
    __tablename__ = "room_members"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    joined_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=True)
    room = relationship("Room", back_populates="members")
    user = relationship("User", back_populates="room_members")

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    content: Mapped[str] = mapped_column(Text())
    is_bot: Mapped[bool] = mapped_column(Boolean(), default=False)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    room = relationship("Room", back_populates="messages")
    user = relationship("User", back_populates="messages")

class Inventory(Base):
    __tablename__ = "inventory"

    product_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_name = Column(String(255), nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    safety_stock_level = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    owner = relationship("User", backref="inventory_items")

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
