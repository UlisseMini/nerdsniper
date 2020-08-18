import aiohttp
import asyncio
import os
import twitter
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class User(BaseModel):
    description: str
    name: str
    username: str
    id: int # unsigned 64bit int
    pinned_tweet_id: Optional[int] # unsigned 64bit int
    created_at: datetime # 32bit, until 2038 :P
    location: Optional[str] = None

    verified: bool
    protected: bool

    followers_count: int # unsigned 32bit int
    following_count: int # unsigned 32bit int
    tweet_count: int     # unsigned 32bit int
    listed_count: int    # unsigned 32bit int

    url: Optional[str] = None


USER_FIELDS = 'description,url,public_metrics,location,created_at,pinned_tweet_id,protected,verified'

def user_from_data(d: dict) -> User:
    return User(
        description = d['description'],
        name = d['name'],
        username = d['username'],
        id = d['id'],
        pinned_tweet_id = d.get('pinned_tweet_id'),
        created_at = d['created_at'],
        location = d.get('location'),

        protected = d['protected'],
        verified = d['verified'],

        followers_count = d['public_metrics']['followers_count'],
        following_count = d['public_metrics']['following_count'],
        tweet_count     = d['public_metrics']['tweet_count'],
        listed_count    = d['public_metrics']['listed_count'],

        url = d.get('url'),
    )



async def fetch_user(api, username: str) -> User:
    url = 'https://api.twitter.com/2/users/by/username/' + username
    resp = await api.get(url, params={
        'user.fields': USER_FIELDS,
        # 'expansions': 'pinned_tweet_id',
        # 'tweet.fields': 'author_id,created_at,text',
    })
    return user_from_data(resp['data'])


async def main(api):
    user = await fetch_user(api, 'MiniUlisse')

    print(repr(user))
    import pdb; pdb.set_trace()

async def init():
    bearer_token = os.environ['bearer']

    async with twitter.API([bearer_token]) as api:
        await main(api)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init())
