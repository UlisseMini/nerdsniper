import aiohttp
import asyncio
import asyncpg
import os
import json
import dateutil.parser

STREAM_URL = 'https://api.twitter.com/2/tweets/sample/stream'

PARAMS = {
    "expansions": "attachments.media_keys,author_id,entities.mentions.username,geo.place_id,in_reply_to_user_id,referenced_tweets.id,referenced_tweets.id.author_id",
    "tweet.fields": "author_id,conversation_id,created_at,entities,geo,id,in_reply_to_user_id,lang,public_metrics,possibly_sensitive,referenced_tweets,source,text,withheld",
    "user.fields": "created_at,description,entities,id,location,name,pinned_tweet_id,protected,public_metrics,url,username,verified,withheld",
}

U_FIELDS = 'id,name,username,url,description,location,created_at,pinned_tweet_id,protected,verified,followers_count,following_count,tweet_count'.split(',')
T_FIELDS = 'text,id,author_id,created_at,in_reply_to_user_id,lang,retweet_count,reply_count,like_count,quote_count,possibly_sensitive,conversation_id,source'.split(',')

T_TABLE = 'tweets'
U_TABLE = 'users'

async def fetcher(s, bearer, queue):
    async with s.get(
        STREAM_URL,
        headers={"Authorization": "Bearer " + bearer},
        params=PARAMS,
    ) as resp:
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


def prepare(obj):
    """
    Prepare object does a few things
    1. Flatten public metrics
    2. Convert id, tweets_count, ... fields from string to int
    3. Parse created_at into a datetime object
    >>> prepare({'id': '1', 'public_metrics': {'tweet_id': '2', 'foo': 'bar'}})
    {'id': 1, 'tweet_id': 2, 'foo': 'bar'}
    >>> prepare({'id': '123', 'tweets_count': '69'})
    {'id': 123, 'tweets_count': 69}
    >>> prepare({'created_at': '2021-03-27T15:09:37.000Z'})
    {'created_at': datetime.datetime(2021, 3, 27, 15, 9, 37)}
    """

    # flatten public metrics
    if obj.get('public_metrics'):
        for k, v in obj['public_metrics'].items():
            obj[k] = v
        del obj['public_metrics']

    # convert *id* and *count* to integers
    for k in obj:
        if 'id' in k or 'count' in k:
            obj[k] = int(obj[k])

    # parse created_at
    if obj.get('created_at'):
        obj['created_at'] = dateutil.parser.parse(obj['created_at']).replace(tzinfo=None)

    return obj



def tweet_from(o):
    return [o.get(k) for k in T_FIELDS]


def user_from(o):
    return [o.get(k) for k in U_FIELDS]



async def update_db_tweets(conn, tweets):
    print(f'inserting {len(tweets)} new tweets')
    result = await conn.copy_records_to_table(
        T_TABLE, records=tweets, columns=T_FIELDS,
    )
    print(result)



async def update_db_users(conn, users):
    print(f'inserting {len(users)} new users')
    result = await conn.copy_records_to_table(
        U_TABLE, records=users, columns=U_FIELDS,
    )
    print(result)



def get_users(items):
    return [user_from(prepare(obj)) for obj in items]


def get_tweets(items):
    return [tweet_from(prepare(obj)) for obj in items]


async def remove_duplicates(conn, items, table):
    """
    Remove duplicates in 'items' with respect to 'id' in db table 'table'
    """

    items_by_id = {x['id']: x for x in items}

    duplicates = await conn.fetch(
        f'SELECT id FROM {table} WHERE id IN ({",".join(items_by_id.keys())})'
    )

    duplicate_ids = set(str(x['id']) for x in duplicates) # x['id'] is int
    ret = [x for xid, x in items_by_id.items() if xid not in duplicate_ids]
    return ret



async def update_db_daemon(conn, queue, BUF_SIZE=1000):
    tweets = []
    users = []

    i = 1
    nu = 0
    nt = 0
    while item := await queue.get():
        print(f'i: {i} tweets: {nt} users: {nu}')
        i += 1

        includes = item.get('includes') or {}

        if d := item.get('data'):
            tweets.append(d)

        tweets += includes.get('tweets') or []
        users += includes.get('users') or []

        nt += len(includes.get('tweets') or []) + 1
        nu += len(includes.get('users') or [])

        if len(tweets) > BUF_SIZE:
            tweets = await remove_duplicates(conn, tweets, T_TABLE)
            await update_db_tweets(conn, get_tweets(tweets))
            tweets.clear()

        if len(users) > BUF_SIZE:
            users = await remove_duplicates(conn, users, U_TABLE)
            await update_db_users(conn, get_users(users))
            users.clear()



async def main(s, conn):
    bearer_tokens = os.environ['BEARER_TOKENS'].split(',')
    queue = asyncio.Queue(maxsize=100)
    fetchers = [asyncio.create_task(fetcher_retry(s, bearer, queue)) for bearer in bearer_tokens]
    db_updater = asyncio.create_task(update_db_daemon(conn, queue))

    try:
        await db_updater
    except asyncio.CancelledError:
        pass


    print('waiting for fetchers...')
    for f in fetchers:
        f.cancel()
        await f



async def entry():
    conn = await asyncpg.connect(
        user=os.environ.get('PG_USER')     or 'postgres',
        password=os.environ.get('PG_PASS') or 'postgres',
        database=os.environ.get('PG_DB')   or 'postgres',
    )
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
