# encoding: utf-8

import logging

from server import htnd_client, sio
BLOCKS_CACHE = []
TASKS = []
logger = logging.getLogger(__name__)


async def config():
    logger.info("Starting block notification subscription")

    async def on_new_block(e):
        try:
            block_info = e["blockAddedNotification"]["block"]
        except KeyError:
            logger.warning("Received unexpected block notification payload: %s", e)
            return

        global BLOCKS_CACHE
        emit_info = {
            'block_hash': block_info["verboseData"]["hash"],
            'difficulty': block_info["verboseData"]["difficulty"],
            'blueScore': block_info["header"]["blueScore"],
            'timestamp': block_info["header"]["timestamp"],
            'txCount': len(block_info["transactions"]),
            'txs': [{
                'txId': x["verboseData"]["transactionId"],
                'outputs': [(output["verboseData"]["scriptPublicKeyAddress"], output["amount"]) for output in
                            x["outputs"][-20:]]
            } for x in block_info["transactions"][-20:]]
        }

        logger.info(
            "Received new block hash=%s blueScore=%s txCount=%s",
            emit_info["block_hash"],
            emit_info["blueScore"],
            emit_info["txCount"],
        )

        BLOCKS_CACHE.append(emit_info)
        if len(BLOCKS_CACHE) > 10:
            BLOCKS_CACHE.pop(0)

        logger.debug("Block cache size is now %s", len(BLOCKS_CACHE))

        try:
            await sio.emit("new-block", emit_info, room="blocks")
        except Exception:
            logger.exception("Failed emitting new-block for hash=%s", emit_info["block_hash"])
            raise

        logger.info("Emitted new-block event for hash=%s to room=blocks", emit_info["block_hash"])

    try:
        await htnd_client.notify("notifyBlockAddedRequest", None, on_new_block)
    except Exception:
        logger.exception("Block notification subscription terminated unexpectedly")
        raise


@sio.on("last-blocks")
async def get_last_blocks(sid, msg):
    logger.info("Socket %s requested last-blocks; cache_size=%s", sid, len(BLOCKS_CACHE))
    await sio.emit("last-blocks", BLOCKS_CACHE, to=sid)
