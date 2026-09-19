import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

SCHEMA = "langgraph"


@asynccontextmanager
async def open_checkpointer() -> AsyncIterator[AsyncPostgresSaver]:
    db_url = os.getenv("CHECKPOINT_DB_URL", "postgresql://stock:stock@localhost:5433/stockdb")

    async with AsyncConnectionPool(
        db_url,
        open=False,
        # autocommit, prepare_threshold and row_factory are required by AsyncPostgresSaver.
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
            "options": f"-c search_path={SCHEMA}",
        },
    ) as pool:
        async with pool.connection() as connection:
            await connection.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        yield checkpointer
