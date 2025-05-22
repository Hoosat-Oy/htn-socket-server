# encoding: utf-8
import asyncio

from htnd.HtndClient import HtndClient
# pipenv run python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. ./protos/rpc.proto ./protos/messages.proto ./protos/p2p.proto
from htnd.HtndThread import HtndCommunicationError

class NodeNotIndexedError(Exception):
    """Custom exception indicating the node's UTXO is not indexed."""
    pass

class HtndMultiClient(object):
    def __init__(self, hosts: list[str]):
        self.htnds = [HtndClient(*h.split(":")) for h in hosts]

    def __get_htnd(self):
        for k in self.htnds:
            if k.is_utxo_indexed:
                return k

    async def initialize_all(self):
        tasks = [asyncio.create_task(k.ping()) for k in self.htnds]

        for t in tasks:
            await t


    async def request(self, command, params=None, timeout=5):
        try:
            htnd = self.__get_htnd()
            if htnd is not None:
                return await htnd.request(command, params, timeout=timeout)
            else:
                raise NodeNotIndexedError("Did not find a node that hash UTXO indexed")
        except HtndCommunicationError:
            await self.initialize_all()
            htnd = self.__get_htnd()
            if htnd is not None:
                return await htnd.request(command, params, timeout=timeout)
            else:
                raise NodeNotIndexedError("Did not find a node that hash UTXO indexed")

    async def notify(self, command, params, callback):
        htnd = self.__get_htnd()
        if htnd is not None:
            return await htnd.notify(command, params, callback)
        else:
            raise NodeNotIndexedError("Did not find a node that hash UTXO indexed")
