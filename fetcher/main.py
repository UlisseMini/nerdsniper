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


async def fetcher_retry(s, bearer, queue):
    try:
        while True:
            await fetcher(s, bearer, queue)
            print('Disconnected from stream! reconnecting in 60s...')
            await asyncio.sleep(60)

    except asyncio.CancelledError:
        pass


async def update_db():
    pass


async def main(s, conn):
    bearer_tokens = os.environ['BEARER_TOKENS'].split(',')
    queue = asyncio.Queue(maxsize=100)
    fetchers = [asyncio.create_task(fetcher_retry(s, bearer, queue)) for bearer in bearer_tokens]

    try:
        while item := await queue.get():
            print(item)
    except asyncio.CancelledError:
        print('canceled!')


    print('waiting for fetchers...')
    for f in fetchers:
        f.cancel()
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
    task = loop.create_task(entry())

    try:
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        print('\nGot interrupt, shutting down...')
    finally:
        task.cancel()
        loop.run_until_complete(task)
        task.exception()

        loop.close()
