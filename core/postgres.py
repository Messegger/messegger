import asyncpg
import asyncio
from core.config import config

class Database:
    def __init__(self):
        self.connection: asyncpg.Connection

    async def connect(self, config: dict):
        self.connection = await asyncpg.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
        )

    async def execute(self, query: str, *args):
        await self.connection.execute(query, *args)

    async def simple_insert(self, table: str, **kwargs):
        columns = ', '.join(kwargs.keys())
        values = ', '.join(f'${i+1}' for i in range(len(kwargs)))
        await self.execute(f"INSERT INTO {table} ({columns}) VALUES ({values})", *kwargs.values())

    async def simple_update(self, table: str, condition: str, **data):
        columns = ', '.join(f'{key} = ${i+1}' for i, (key, _) in enumerate(data.items()))
        await self.execute(f"UPDATE {table} SET {columns} WHERE {condition}", *data.values())

    async def fetch(self, query: str, *args):
        return await self.connection.fetch(query, *args)

    #async def fetchrow(self, query: str, *args):
    #    return await self.connection.fetchrow(query, *args)

    async def disconnect(self):
        await self.connection.close()


db = Database()

async def _delete_old_messages():
    while True:
        await db.execute("DELETE FROM messages WHERE timestamp < NOW() - INTERVAL '30 days'")
        await asyncio.sleep(60)

async def init_db():
    await db.connect(config["postgresql"])
    with open("schema.sql", "r") as file:
        await db.execute(file.read())
    asyncio.create_task(_delete_old_messages())
