import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:12345678@localhost:5432/smsos_dev"

async def migrate():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        print("Altering inbound_messages columns...")
        await conn.execute(text("ALTER TABLE inbound_messages ALTER COLUMN from_number TYPE VARCHAR(64);"))
        await conn.execute(text("ALTER TABLE inbound_messages ALTER COLUMN to_number TYPE VARCHAR(64);"))
        
        print("Altering outbound_messages columns...")
        await conn.execute(text("ALTER TABLE outbound_messages ALTER COLUMN to_number TYPE VARCHAR(64);"))
        
        print("Altering customers columns...")
        await conn.execute(text("ALTER TABLE customers ALTER COLUMN phone_number TYPE VARCHAR(64);"))

        print("Altering conversation_states columns...")
        await conn.execute(text("ALTER TABLE conversation_states ALTER COLUMN from_number TYPE VARCHAR(64);"))
        print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
