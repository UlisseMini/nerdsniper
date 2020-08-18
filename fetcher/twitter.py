import aiohttp
import asyncio

class API:
    """
    A twitter API instance. This object takes a list of bearer tokens,
    and keeps track of their ratelimits. thus if token A is on cooldown, token B can be used.
    """
    def __init__(self, tokens: [str] = None):
        self.sess = aiohttp.ClientSession()
        self.tokens = tokens

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.sess.close()


    def headers(self):
        # TODO: cycle through active tokens, use ones not on cooldown
        return {
            'authorization': 'Bearer ' + self.tokens[0],
        }

    async def get(self, url, params={}):
        async with self.sess.get(url, headers=self.headers(), params=params) as r:
            return await r.json()



