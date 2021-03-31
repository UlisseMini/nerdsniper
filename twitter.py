"""
Twitter API wrappers, focused on making requests with a pool of tokens
Only bearer tokens for now, but user auth shoulden't be hard to add
"""

import os
import aiohttp
import aiohttp.client_exceptions
import json
import asyncio

STREAM_TIMEOUT = 10


class API():
    def __init__(self, bearer_tokens):
        assert type(bearer_tokens) == list
        self.bearer_tokens = bearer_tokens
        self.i = 0 # current bearer
        self.s = aiohttp.ClientSession()

    async def close(self):
        await self.s.close()

    def get_auth(self):
        self.i = (self.i + 1) % len(self.bearer_tokens)
        return 'Bearer ' + self.bearer_tokens[self.i]

    async def get_json(self, url: str, *args, headers={}, **kwargs):
        headers['Authorization'] = self.get_auth()
        async with self.s.get(url, *args, headers=headers, **kwargs) as resp:
            # TODO: Check for invalid json
            return await resp.json()

    async def followers(self, userid: int, *args, **kwargs):
        url = f'https://api.twitter.com/2/users/{userid}/followers'
        return await self.get_json(url, *args, **kwargs)

    async def following(self, userid: int):
        url = f'https://api.twitter.com/2/users/{userid}/following'
        return await self.get_json(url)

    async def sampled_stream(self, timeout=STREAM_TIMEOUT, headers={}, **kwargs):
        """Sampled stream of tweets until we get no lines from the stream for
        'timeout' seconds. then we assume something has gone wrong and return None.
        Restarting can be done with sampled_stream_restart, which is just an infinite loop
        of sampled_stream.
        """

        url = 'https://api.twitter.com/2/tweets/sample/stream'
        headers['Authorization'] = self.get_auth()
        async with self.s.get(url, headers=headers, **kwargs) as resp:
            try:
                while True:
                    line = await asyncio.wait_for(resp.content.readline(), timeout)
                    if line.strip() == b'':
                        continue
                    yield json.loads(line.decode())
            # ClientPayloadError seems to be a bug in aiohttp, or maybe twitter is sending invalid data
            except (asyncio.TimeoutError, aiohttp.client_exceptions.ClientPayloadError):
                pass

    async def sampled_stream_restart(self, retry_delay=10, timeout=STREAM_TIMEOUT, **kwargs):
        while True:
            # yield from doesn't work in async generators https://stackoverflow.com/a/47378063
            async for blob in self.sampled_stream(timeout=timeout, **kwargs):
                yield blob

            print(f'Disconnected from stream, retrying in {retry_delay}s')
            await asyncio.sleep(retry_delay)


async def main():
    bearer_tokens = os.environ['BEARER_TOKENS'].split(',')
    api = API(bearer_tokens)

    with open('tweets.ndjson', 'w') as f:
        async for blob in api.sampled_stream_restart():
            print(blob['data'])
            json.dump(blob, f)

    await api.close()

    # followers = await api.following(12)
    # print(followers)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
