import aiohttp
import asyncio
import asyncpg
import os
import json

STREAM_URL = 'https://api.twitter.com/2/tweets/sample/stream'

async def fetcher(s, bearer, queue):
    async with s.get(STREAM_URL, headers={"Authorization": "Bearer " + bearer}) as resp:
        async for line in resp.content:
            if line.strip() == b'':
                continue

            data = json.loads(line.decode())
            await queue.put(data)


async def update_db():
    pass


async def main(s, conn):
    print(s, conn); exit()

    bearer_tokens = os.environ['BEARER_TOKENS'].split(',')
    queue = asyncio.Queue(maxsize=100)
    fetchers = [asyncio.create_task(fetcher(s, bearer, queue)) for bearer in bearer_tokens]

    while True:
        item = await queue.get()
        if item is None:
            break

        print(item)



    for f in fetchers:
        await f



async def entry():
    conn = await asyncpg.connect()
    s = aiohttp.ClientSession()
    try:
        await main(s, conn)

    finally:
        await conn.close()
        await s.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(entry())
    finally:
        loop.close()
