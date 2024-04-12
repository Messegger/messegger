import asyncio
import signal
from core.main import client
from core.postgres import db, init_db

async def signal_handler():
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    await asyncio.gather(*tasks, return_exceptions=True)
    await db.disconnect()
    await client.close()

async def main():
    await init_db()
    await client.start(client.config["bot"]["token"], reconnect=True)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, loop.create_task, signal_handler())
    loop.add_signal_handler(signal.SIGTERM, loop.create_task, signal_handler())
    loop.run_until_complete(main())
