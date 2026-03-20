# encoding: utf-8
import asyncio
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

print(
    f"Loaded: {sockets.join_room}"
    f"{periodic_coin_supply} {periodical_blockdag} {periodical_blue_score}")

BLOCKS_TASK: Optional[Task] = None


async def start_blocks_task():
    global BLOCKS_TASK

    if BLOCKS_TASK is not None and not BLOCKS_TASK.done():
        return BLOCKS_TASK

    BLOCKS_TASK = asyncio.create_task(blocks.config())
    return BLOCKS_TASK


@app.on_event("startup")
async def startup():
    # find htnd before staring webserver
    await htnd_client.initialize_all()
    await start_blocks_task()


@app.on_event("startup")
@repeat_every(seconds=5)
async def watchdog():
    global BLOCKS_TASK

    if BLOCKS_TASK is None:
        await htnd_client.initialize_all()
        await start_blocks_task()
        return

    try:
        exception = BLOCKS_TASK.exception()
    except InvalidStateError:
        return
    except asyncio.CancelledError:
        print("Watch found cancelled block task. Reinitializing htnds and restarting task")
        await htnd_client.initialize_all()
        await start_blocks_task()
    else:
        if not BLOCKS_TASK.done():
            return

        if exception is None:
            print("Watch found completed block task. Reinitializing htnds and restarting task")
        else:
            print(f"Watch found an error! {exception}\n"
                  f"Reinitialize htnds and start task again")

        await htnd_client.initialize_all()
        await start_blocks_task()


@app.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url='/docs')


if __name__ == '__main__':
    if os.getenv("DEBUG"):
        import uvicorn

        uvicorn.run(app)
