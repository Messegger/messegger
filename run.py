import asyncio
import signal
from core.main import client
from core.postgres import db, init_db

async def signal_handler():
    await client.close()
    await db.disconnect()

async def main():
    await init_db()
    await client._load_extensions()
    await client.start(client.config["bot"]["token"], reconnect=True)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, lambda: loop.create_task(signal_handler()))
    loop.add_signal_handler(signal.SIGTERM, lambda: loop.create_task(signal_handler()))
    loop.run_until_complete(main())
