import aiohttp
import asyncio
import asyncpg
import os
import json
import dateutil.parser
import twitter

PARAMS = {
    "expansions": "attachments.media_keys,author_id,entities.mentions.username,geo.place_id,in_reply_to_user_id,referenced_tweets.id,referenced_tweets.id.author_id",
    "tweet.fields": "author_id,conversation_id,created_at,entities,geo,id,in_reply_to_user_id,lang,public_metrics,possibly_sensitive,referenced_tweets,source,text,withheld,context_annotations",
    "user.fields": "created_at,description,entities,id,location,name,pinned_tweet_id,protected,public_metrics,url,username,verified,withheld",
}

U_FIELDS = 'id,name,username,url,description,location,created_at,pinned_tweet_id,protected,verified,followers_count,following_count,tweet_count'.split(',')
T_FIELDS = 'text,id,author_id,created_at,in_reply_to_user_id,retweet_count,reply_count,like_count,quote_count,possibly_sensitive,conversation_id,source'.split(',')

T_TABLE = 'tweets'
U_TABLE = 'users'

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


async def remove_duplicates(conn, items, table):
    """
    Remove duplicates in 'items' with respect to 'id' in db table 'table'
    **NOTE: items are before prepare() so item['id'] is str, but dup['id'] is int (from db)
    """

    items_by_id = {int(item['id']): item for item in items}

    duplicates = await conn.fetch(
        f'SELECT id FROM {table} WHERE id IN ({",".join(item["id"] for item in items)})'
    )

    duplicate_ids = set(dup['id'] for dup in duplicates)
    ret = [item for itemid, item in items_by_id.items() if itemid not in duplicate_ids]
    return ret


async def update_db(conn, items, table, fields):
    """
    Update table with items 'items' and fields 'fields'.
    fields must also be table columns!
    """
    def to_record(item):
        item = prepare(item)
        return [item.get(k) for k in fields]

    records = [to_record(item) for item in items]

    print(f'COPY {len(records)} RECORDS TO {table}')
    result = await conn.copy_records_to_table(
        table, records=records, columns=fields,
    )
    print(result)


async def add_users_to_db(conn, users):
    users_uniq = await remove_duplicates(conn, users, U_TABLE)
    print(f'Removed {len(users) - len(users_uniq)} duplicate users')
    await update_db(conn, users_uniq, U_TABLE, U_FIELDS)


async def add_tweets_to_db(conn, tweets):
    tweets_uniq = await remove_duplicates(conn, tweets, T_TABLE)
    print(f'Removed {len(tweets) - len(tweets_uniq)} duplicate tweets')
    await update_db(conn, tweets_uniq, T_TABLE, T_FIELDS)



    for tweet in tweets_uniq:
        if tweet.get('context_annotations') is None:
            continue

        ctx_anno = tweet['context_annotations']
        for anno in ctx_anno:
            domain, entity = anno['domain'], anno['entity']

            # TODO: Use remove_duplicates instead of executing each query (slow)
            await conn.execute('''
            INSERT INTO context_annotations (domain_id, entity_id, tweet_id) VALUES ($1, $2, $3)
            ''', int(domain['id']), int(entity['id']), int(tweet['id']))

            await conn.execute(
                'INSERT INTO entity_names (entity_id, name) VALUES ($1, $2) ON CONFLICT DO NOTHING',
                int(entity['id']), entity['name']
            )

            await conn.execute(
                'INSERT INTO domain_names (domain_id, name) VALUES ($1, $2) ON CONFLICT DO NOTHING',
                int(domain['id']), domain['name']
            )



async def main(api, conn, BUF_SIZE=100):
    tweets = []
    users = []

    i = 1
    async for item in api.sampled_stream_restart(params=PARAMS):
        print(f'i: {i}' + ' '*20, end='\r')
        i += 1

        # is it a retweet? we don't save tweets that are retweets.
        rt = False
        if d := item.get('data'):
            if d['lang'] != 'en':
                continue

            rt = d['text'].startswith('RT ')
            if not rt:
                tweets.append(d)

        includes = item.get('includes') or {}
        users += includes.get('users') or []
        if not rt:
            tweets += includes.get('tweets') or []

        if len(tweets) > BUF_SIZE:
            print()
            await add_tweets_to_db(conn, tweets)
            tweets.clear()

        if len(users) > BUF_SIZE:
            print()
            await add_users_to_db(conn, users)
            users.clear()


async def entry():
    conn = await asyncpg.connect(
        user=os.environ.get('PG_USER')     or 'postgres',
        password=os.environ.get('PG_PASS') or 'postgres',
        database=os.environ.get('PG_DB')   or 'postgres',
    )
    bearer_tokens = os.environ['BEARER_TOKENS'].split(',')
    api = twitter.API(bearer_tokens)
    try:
        await main(api, conn)
    finally:
        await conn.close()
        await api.close()


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
