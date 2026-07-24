import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect("postgresql://postgres:12345678@localhost:5432/postgres")
    for db_name in ["smsos_dev", "smsos_test"]:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Created database {db_name}")
        else:
            print(f"Database {db_name} already exists")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
