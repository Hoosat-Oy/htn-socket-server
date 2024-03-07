# encoding: utf-8

from server import htnd_client


async def get_blockdag():
    """
    Get some global Kaspa BlockDAG information
    """
    resp = await htnd_client.request("getBlockDagInfoRequest")
    return resp["getBlockDagInfoResponse"]
