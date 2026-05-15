"""
Test configuration and shared fixtures.

Env vars required:
- BOT_TOKEN, ENCRYPTION_SECRET, DATABASE_URL: stubbed (set below) for import-time reads in config.py
- TEST_DATABASE_URL: required for DB-backed tests. If unset, those tests are skipped.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Stub env vars BEFORE any project module is imported.
os.environ.setdefault("BOT_TOKEN", "test:stub")
os.environ.setdefault("ENCRYPTION_SECRET", "test-secret-key-for-tests-only")
os.environ.setdefault("DATABASE_URL", "postgresql://stub/stub")

# Make project root importable.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncpg
import pytest
import pytest_asyncio

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
SCHEMA_PATH = PROJECT_ROOT / "schema.sql"


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests in tests/integration/ if TEST_DATABASE_URL is not set."""
    if TEST_DATABASE_URL:
        return
    skip_db = pytest.mark.skip(reason="TEST_DATABASE_URL not set")
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(skip_db)


# ---------- DB fixtures ----------

@pytest_asyncio.fixture(scope="session")
async def db_pool():
    """Session-scoped asyncpg pool. Runs schema once, tears down at end."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set")

    pool = await asyncpg.create_pool(TEST_DATABASE_URL, min_size=1, max_size=4)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    async with pool.acquire() as conn:
        # Drop everything first so the schema applies cleanly on a re-used DB.
        await conn.execute("""
            DROP TABLE IF EXISTS sessions CASCADE;
            DROP TABLE IF EXISTS subscriptions CASCADE;
            DROP TABLE IF EXISTS activity_types CASCADE;
            DROP TABLE IF EXISTS users CASCADE;
        """)
        await conn.execute(schema)
    yield pool
    await pool.close()


@pytest_asyncio.fixture
async def pool(db_pool):
    """Per-test fixture: truncates tables + clears in-process caches so tests are isolated."""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            TRUNCATE sessions, subscriptions, users RESTART IDENTITY CASCADE;
        """)
    # Clear module-level caches in db.py
    import db
    db._lang_cache.clear()
    db._activity_cache.clear()
    yield db_pool


# ---------- Aiogram FSM context ----------

@pytest_asyncio.fixture
async def fsm():
    """Returns a fresh FSMContext backed by an in-memory storage."""
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey
    from aiogram.fsm.storage.memory import MemoryStorage

    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=999, user_id=999)
    return FSMContext(storage=storage, key=key)


# ---------- Mock event helpers ----------

def make_callback(*, data: str, user_id: int = 999, lang_code: str = "uk") -> MagicMock:
    """Create a mock CallbackQuery with an awaitable .message and .answer()."""
    msg = MagicMock()
    msg.answer = AsyncMock()
    msg.edit_text = AsyncMock()
    msg.edit_reply_markup = AsyncMock()
    msg.chat = MagicMock(id=user_id)
    msg.bot = MagicMock()
    msg.bot.edit_message_reply_markup = AsyncMock()

    cb = MagicMock()
    cb.data = data
    cb.from_user = MagicMock(id=user_id, language_code=lang_code,
                             username=f"user{user_id}", first_name="Test")
    cb.message = msg
    cb.answer = AsyncMock()
    cb.bot = msg.bot
    return cb


def make_message(*, text: str = "", user_id: int = 999, lang_code: str = "uk",
                 web_app_data: str | None = None) -> MagicMock:
    """Create a mock Message with awaitable .answer() / .bot."""
    msg = MagicMock()
    msg.text = text
    msg.answer = AsyncMock()
    msg.edit_text = AsyncMock()
    msg.chat = MagicMock(id=user_id)
    msg.from_user = MagicMock(id=user_id, language_code=lang_code,
                              username=f"user{user_id}", first_name="Test")
    msg.bot = MagicMock()
    msg.bot.edit_message_reply_markup = AsyncMock()
    if web_app_data is not None:
        msg.web_app_data = MagicMock(data=web_app_data)
    else:
        msg.web_app_data = None
    return msg


@pytest.fixture
def callback():
    return make_callback


@pytest.fixture
def message():
    return make_message
