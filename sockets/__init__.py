# encoding: utf-8

import logging

from server import sio
from sockets.blockdag import emit_blockdag
from sockets.bluescore import emit_bluescore
from sockets.coinsupply import emit_coin_supply

VALID_ROOMS = ["blocks", "coinsupply", "blockdag", "bluescore"]
logger = logging.getLogger(__name__)


@sio.on("join-room")
async def join_room(sid, room_name):
    if room_name in VALID_ROOMS:
        logger.info("Socket %s joining room %s", sid, room_name)
        sio.enter_room(sid, room_name)

        if room_name == "blockdag":
            await emit_blockdag()

        if room_name == "coinsupply":
            await emit_coin_supply()

        if room_name == "bluescore":
            await emit_bluescore()
    else:
        logger.warning("Socket %s attempted to join invalid room %s", sid, room_name)

