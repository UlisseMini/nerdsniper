import asyncio
import asyncpg as pg
import aiohttp
import json
import itertools
import os
import time
import math
import sys

# <o/ 1. Get streaming data from users table using copy
# 2. Reformat that data, parse the date
# 3. Send that along the stream to elasticsearch's bulk api

FIELDS = 'id,name,username,url,description,location,created_at,' \
       + 'protected,verified,followers_count,following_count,tweet_count'


ES_URL = "http://elasticsearch:9200"
ES_INDEX ="user"
RECORDS_TABLE = "users"


def process_for_es(record: dict):
    """
    Return a string which is sent along the streaming POST to elasticsearch.
    """

    record['created_at'] = record['created_at'].isoformat()

    _id = record['id']
    del record['id']

    s1 = json.dumps({ 'index': {'_id': _id} })
    s2 = json.dumps(record)

    return s1 + '\n' + s2 + '\n'


async def records_stream(conn):
    async with conn.transaction():
        cursor = conn.cursor(f'SELECT {FIELDS} FROM {RECORDS_TABLE}')
        async for record in cursor:
            yield dict(record)



async def elastic_body_stream(record_stream):
    async for record in record_stream:
        ndjson_str = process_for_es(record)
        yield ndjson_str.encode()




async def limit(agen, limit):
    try:
        for _ in range(limit):
            item = await agen.__anext__()
            yield item
    except StopAsyncIteration:
        pass



async def estimate_num_records(conn):
    record_num = await conn.fetchval(f"SELECT reltuples::bigint FROM pg_catalog.pg_class WHERE relname = '{RECORDS_TABLE}'")
    return record_num


def eprint(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


BATCH_SIZE = 10_000
async def main(conn, s):
    records = records_stream(conn)
    post_body = elastic_body_stream(records)

    print('Getting table size estimate...', end=' ', flush=True)
    num_records = await estimate_num_records(conn)
    print(f'{num_records} done')

    num_batches = math.ceil(num_records / BATCH_SIZE)
    try:
        errors = 0 # total number of record errors
        for batch in itertools.count():
            print(f'batch {batch}/{num_batches}', end=' ', flush=True)
            batch_iter = limit(post_body, BATCH_SIZE)

            start = time.time()
            async with s.post(
                f'{ES_URL}/{ES_INDEX}/_doc/_bulk',
                data=batch_iter,
                headers={'Content-Type': 'application/x-ndjson'}
            ) as resp:
                j = await resp.json()

                errors = 0
                try:
                    for item in j['items']:
                        x = item['index']
                        # error if status code is not in the 200 range
                        if (x['status'] // 100) != 2:
                            eprint(json.dumps(x))
                            errors += 1
                except IndexError:
                    eprint(json.dumps(j))



            took = time.time() - start
            print(f'errors: {errors} took: {took:.3f}s')

    except StopIteration as e:
        print(e)




async def entry():
    conn = await pg.connect()
    s = aiohttp.ClientSession()
    try:
        await main(conn, s)
    finally:
        await conn.close()
        await s.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(entry())
    finally:
        loop.close()

