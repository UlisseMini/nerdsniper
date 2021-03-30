import asyncio
import json

ENDPOINT_URL = 'https://api.twitter.com/2/users/{id}/{endpoint}'

async def get_follow(s, userid, bearer, endpoint):
    "Endpoint can be followers or following"

    url = ENDPOINT_URL.format(id=userid, endpoint=endpoint)
    headers = {"Authorization": "Bearer " + bearer}
    async with s.get(url=url, headers=headers) as resp:
        text = await resp.text()
        return text


async def get_follow_retry(s, userid, bearers, endpoint):
    # TODO: Fix ordering, currently we go forward->back but with large amount of bearer tokens
    # that will constantly request with a ratelimited one, use a dict with time values.

    while True:
        for bearer in bearers:
            resp_text = await get_follow(s, userid, bearer, endpoint)
            # TODO: Less ad-hoc testing
            if 'Rate limit exceeded' in resp_text:
                continue # try next token

            try:
                data = json.loads(resp_text)
                if errors := data.get('errors'):
                    print(errors)
                    return None

                return data
            except json.JSONDecodeError:
                # TODO: Add logging to file so errors aren't missed
                print('FAILED TO DECODE JSON')
                print(resp_text)
                return None

        # wait a minute before retrying each token
        print(f'Waiting 60s for {endpoint} endpoint ratelimit')
        await asyncio.sleep(60)


async def get_null(conn, table, limit=100):
    """
    Both following and followers have column same as table name.
    """
    return await conn.fetch(f'SELECT userid FROM {table} WHERE {table} IS NULL LIMIT {limit}')


async def follows_update(s, conn, bearers, endpoint):
    records = await get_null(conn, endpoint)
    for record in records:
        userid = record['userid']
        follows = await get_follow_retry(s, userid, bearers, endpoint)
        if follows is None: # user does not exist, etc error
            continue

        follows_ids = [int(user['id']) for user in follows['data']]

        print(f'UPDATE {endpoint} userid={userid} add {len(follows_ids)}')
        await conn.execute(
            f'UPDATE {endpoint} SET {endpoint} = $1 WHERE userid={userid}',
            follows_ids
        )

async def follows_daemon(s, conn, bearers):
    try:
        while True:
            for endpoint in ('followers', 'following'):
                await follows_update(s, conn, bearers, endpoint)

            await asyncio.sleep(120)

    except asyncio.CancelledError:
        pass


import aiohttp

async def main():
    async with aiohttp.ClientSession() as s:
        followers()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
