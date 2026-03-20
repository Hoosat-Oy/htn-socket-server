# encoding: utf-8

import logging

from server import htnd_client, sio
BLOCKS_CACHE = []
TASKS = []
logger = logging.getLogger(__name__)


async def config():
    logger.info("Starting block notification subscription")

    async def on_new_block(e):
        if "notifyBlockAddedResponse" in e:
            logger.info("Block notification subscription acknowledged")
            return

        block_added_notification = e.get("blockAddedNotification")
        if not block_added_notification:
            logger.warning("Received unexpected block notification payload: %s", e)
            return

        block_info = block_added_notification.get("block") or {}
        header = block_info.get("header") or {}
        verbose_data = block_info.get("verboseData") or {}
        transactions = block_info.get("transactions") or []
        transaction_ids = verbose_data.get("transactionIds") or []

        tx_count = len(transactions) if transactions else len(transaction_ids)
        rendered_transactions = []
        for transaction in transactions[-20:]:
            transaction_verbose_data = transaction.get("verboseData") or {}
            outputs = transaction.get("outputs") or []
            rendered_transactions.append({
                'txId': transaction_verbose_data.get("transactionId"),
                'outputs': [
                    ((output.get("verboseData") or {}).get("scriptPublicKeyAddress"), output.get("amount"))
                    for output in outputs[-20:]
                ]
            })

        global BLOCKS_CACHE
        emit_info = {
            'block_hash': verbose_data.get("hash"),
            'difficulty': verbose_data.get("difficulty"),
            'blueScore': header.get("blueScore", verbose_data.get("blueScore")),
            'timestamp': header.get("timestamp"),
            'txCount': tx_count,
            'txs': rendered_transactions,
        }

        logger.info(
            "Received new block hash=%s blueScore=%s txCount=%s headerOnly=%s",
            emit_info["block_hash"],
            emit_info["blueScore"],
            emit_info["txCount"],
            verbose_data.get("isHeaderOnly"),
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
