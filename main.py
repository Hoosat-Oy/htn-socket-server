# encoding: utf-8
import asyncio
import logging
import os
from asyncio import Task, InvalidStateError
from typing import Optional

from fastapi_utils.tasks import repeat_every
from starlette.responses import RedirectResponse

import sockets
from server import app, htnd_client
from sockets import blocks
from sockets.blockdag import periodical_blockdag
from sockets.bluescore import periodical_blue_score
from sockets.coinsupply import periodic_coin_supply

logger = logging.getLogger(__name__)

logger.info(
    "Loaded socket handlers: join_room=%s coinsupply=%s blockdag=%s bluescore=%s",
    sockets.join_room,
    periodic_coin_supply,
    periodical_blockdag,
    periodical_blue_score,
)

BLOCKS_TASK: Optional[Task] = None


async def start_blocks_task():
    global BLOCKS_TASK

    if BLOCKS_TASK is not None and not BLOCKS_TASK.done():
        logger.debug("Blocks task already running")
        return BLOCKS_TASK

    logger.info("Creating blocks subscription task")
    BLOCKS_TASK = asyncio.create_task(blocks.config())
    return BLOCKS_TASK


@app.on_event("startup")
async def startup():
    # find htnd before staring webserver
    logger.info("Server startup: initializing htnd clients")
    await htnd_client.initialize_all()
    await start_blocks_task()


@app.on_event("startup")
@repeat_every(seconds=5)
async def watchdog():
    global BLOCKS_TASK

    if BLOCKS_TASK is None:
        logger.warning("Watchdog found no block task; reinitializing htnds and starting one")
        await htnd_client.initialize_all()
        await start_blocks_task()
        return

    try:
        exception = BLOCKS_TASK.exception()
    except InvalidStateError:
        logger.debug("Blocks task still running")
        return
    except asyncio.CancelledError:
        logger.warning("Watchdog found cancelled block task; reinitializing and restarting")
        await htnd_client.initialize_all()
        await start_blocks_task()
    else:
        if not BLOCKS_TASK.done():
            return

        if exception is None:
            logger.warning("Watchdog found completed block task; restarting subscription")
        else:
            logger.error(
                "Watchdog found block task error; reinitializing htnds and restarting",
                exc_info=(type(exception), exception, exception.__traceback__),
            )

        await htnd_client.initialize_all()
        await start_blocks_task()


@app.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url='/docs')


if __name__ == '__main__':
    if os.getenv("DEBUG"):
        import uvicorn

        uvicorn.run(app)
