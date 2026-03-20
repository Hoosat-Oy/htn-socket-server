# encoding: utf-8
import asyncio
import logging

from htnd.HtndClient import HtndClient
# pipenv run python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. ./protos/rpc.proto ./protos/messages.proto ./protos/p2p.proto
from htnd.HtndThread import HtndCommunicationError


logger = logging.getLogger(__name__)


class HtndMultiClient(object):
    def __init__(self, hosts: list[str]):
        self.htnds = [HtndClient(*h.split(":")) for h in hosts]
        self._initialize_lock = asyncio.Lock()
        logger.info("Initialized HtndMultiClient with %s hosts", len(self.htnds))

    def __get_htnd(self):
        for k in self.htnds:
            if k.is_utxo_indexed:
                logger.debug("Selected htnd host %s:%s", k.htnd_host, k.htnd_port)
                return k

        logger.warning("No htnd client is currently marked as UTXO indexed")

    async def initialize_all(self):
        async with self._initialize_lock:
            logger.info("Initializing %s htnd clients", len(self.htnds))
            tasks = [asyncio.create_task(k.ping()) for k in self.htnds]

            for t in tasks:
                await t

            ready_hosts = [f"{k.htnd_host}:{k.htnd_port}" for k in self.htnds if k.is_utxo_indexed]
            logger.info("htnd initialization complete; ready hosts=%s", ready_hosts)

    async def _get_or_initialize_htnd(self):
        htnd = self.__get_htnd()
        if htnd is not None:
            return htnd

        logger.info("No ready htnd found; initializing clients before retrying")
        await self.initialize_all()
        htnd = self.__get_htnd()
        if htnd is None:
            logger.error("No indexed htnd is available after initialization")
            raise HtndCommunicationError("No indexed htnd is available")

        return htnd

    async def __request(self, command, params=None, timeout=30):
        htnd = await self._get_or_initialize_htnd()
        return await htnd.request(command, params, timeout=timeout)

    async def request(self, command, params=None, timeout=30):
        try:
            return await self.__request(command, params, timeout=timeout)
        except HtndCommunicationError:
            logger.warning("Request %s failed; reinitializing htnd clients", command)
            await self.initialize_all()
            return await self.__request(command, params, timeout=timeout)

    async def notify(self, command, params, callback):
        try:
            htnd = await self._get_or_initialize_htnd()
            logger.info("Subscribing to %s on %s:%s", command, htnd.htnd_host, htnd.htnd_port)
            await htnd.notify(command, params, callback)
        except HtndCommunicationError:
            logger.warning("Notify %s failed; reinitializing htnd clients", command)
            await self.initialize_all()
            htnd = await self._get_or_initialize_htnd()
            logger.info("Retrying subscription to %s on %s:%s", command, htnd.htnd_host, htnd.htnd_port)
            await htnd.notify(command, params, callback)
