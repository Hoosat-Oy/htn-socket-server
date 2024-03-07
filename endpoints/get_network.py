# encoding: utf-8

from server import htnd_client


async def get_network():
    """
    Get some global kaspa network information
    """
    resp = await htnd_client.request("getBlockDagInfoRequest")
    return resp["getBlockDagInfoResponse"]
