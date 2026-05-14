import asyncio
import logging
import os

import asyncpg
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import BOT_TOKEN, DATABASE_URL
from handlers import register_handlers
from scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

web = FastAPI()
web.mount("/webapp", StaticFiles(directory="webapp"), name="webapp")


async def main() -> None:
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5, ssl="require")
    log.info("Database connected")

    dp["pool"] = pool

    register_handlers(dp)
    setup_scheduler(bot, pool)

    log.info("Bot starting")
    server = uvicorn.Server(uvicorn.Config(web, host="0.0.0.0", port=8080, log_level="warning"))
    try:
        await asyncio.gather(dp.start_polling(bot), server.serve())
    finally:
        await pool.close()
        log.info("Pool closed")


if __name__ == "__main__":
    asyncio.run(main())
