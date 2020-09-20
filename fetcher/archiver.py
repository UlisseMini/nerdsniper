"""
Tweet objects are piped to us line by line, this script is meant to be ran as
python3 listener.py | python3 archiver.py
Ncat was giving us bullshit race conditions so fuck that, wrote my own ncat <o/
"""

import json
from datetime import datetime
import sys
import gzip
import io


# what order the user data should be in the savefile.
# (this is also used as a header!)
USER_SCHEMA = [
    'id', 'name', 'username', 'url', 'description',
    'created_at', 'pinned_tweet_id', 'protected', 'verified',
    'followers_count', 'following_count', 'tweet_count',
]

TWEET_SCHEMA = [
    "id", "text", "source", "lang",
    "author_id", "conversation_id", "in_reply_to_user_id",
    "created_at", "possibly_sensitive",
    "like_count", "quote_count", "reply_count", "retweet_count",
]

# TODO: Get from args (argparse?)
USERS_FILE = 'users.json.gz'
TWEETS_FILE = 'tweets.json.gz'

userids = set()  # for checking duplicate users.

# the logging module is a bloated piece of shit
def log(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


def serialize(obj, schema, fp):
    json.dump([obj.get(k) for k in schema], fp)


def rm(d, key):
    if d.get(key) is not None:
        del d[key]


def flatten_pubmet(obj):
    # flatten public_metrics
    for k, v in obj['public_metrics'].items():
        obj[k] = v
    del obj['public_metrics']

    return obj


# parse the timestamps used for the twitter api
def iso_to_unix(s):
    # fromisoformat does not support the .000Z extension so, we remove it
    # since fromisoformat just intended to be the inverse of
    # datetime.isoformat().
    # we cast to int for some easy space saving, and to avoid screwing things up
    # later in serilization. (we don't record sub second level accuracy)
    return int(datetime.fromisoformat(s[:-5]).timestamp())


def prepare(obj):
    """
    Prepare obj for serialization, it can be a tweet or user obj.
    NOTE: this does not use the schema, that is done in serialize()
    """

    rm(obj['public_metrics'], 'listed_count')
    obj['created_at'] = iso_to_unix(obj['created_at'])

    return flatten_pubmet(obj)


def process(tweet, userids, users_file, tweets_file):
    new_users = []

    # should always have at least one user, the author.
    for user in tweet['includes']['users']:
        if user['id'] not in userids:
            userids.add(user['id'])
            serialize(prepare(user), USER_SCHEMA, users_file)


    # Save the tweet (data contains tweet data)
    serialize(prepare(tweet['data']), TWEET_SCHEMA, tweets_file)



# mode 'wt' is not supported on some versions of python.
def gzip_open(path, mode='w'):
    return io.TextIOWrapper(gzip.GzipFile(path, mode))

def loop(line, num_tweets, users_file, tweets_file):
    if num_tweets % 100 == 0:
        log(f'tweets: {num_tweets} users: {len(userids)}')

    try:
        tweet = json.loads(line)
        process(tweet, userids, users_file, tweets_file)

    except (json.JSONDecodeError, IndexError, KeyError) as e:
        log(f'Error: {e} parsing: {repr(line)}')


def main():
    with gzip_open(USERS_FILE) as uf, gzip_open(TWEETS_FILE) as tf:
        num_tweets = 0
        log('Waiting for tweets...')
        for line in sys.stdin:
            if line.strip() != '':
                num_tweets += 1
                loop(line, num_tweets, uf, tf)


if __name__ == '__main__':
    main()
