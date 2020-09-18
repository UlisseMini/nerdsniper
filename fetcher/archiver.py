"""
Tweet objects are piped to us line by line, this script is meant to be ran as
ncat -lvkp 1234 | python3 archiver.py
Letting ncat do all the heavy lifting is glorious.
"""

# TODO
# + Implement compress()
# + Implement saving of the users dict once it gets to a large-ish size
#   Have separate dict where users[id] = None for checking if we've seen the user,
#   and another dict where users[id] = userobj, for before we save to non volitile storage.
# - Save tweets to a file, basic streaming with csv/ndjson keys should work

# NOTES:
# We don't save userids set because its saved along with the other users sent to stdout.

import json
from datetime import datetime
from sys import stderr

# ~1-2kb/user, so this is ~2mb at most.
# (save just means print to stdout, I need to fuel my pipe addiction.)
SAVE_EVERY = 1000

# what order the user data should be in the savefile.
# (this is also used as a header!)
SCHEMA = [
    'id', 'name', 'username', 'url', 'description',
    'created_at', 'pinned_tweet_id', 'protected', 'verified',
    'followers_count', 'following_count', 'tweet_count',
]

userids = set() # for checking duplicate users.
users = list()  # saved to disk and cleared every so often.

# the logging module is a bloated piece of shit
def log(*args, **kwargs):
    print(*args, **kwargs, file=stderr)


def serialize_users(users):
    for user in users:
        # Print the user in json list format as defined by schema.
        lst = [user.get(k) for k in SCHEMA]
        print(json.dumps(lst))


def rm(d, key):
    if d.get(key) is not None:
        del d[key]


def compress(user):
    # TODO: Move this into ./fetcher.py for speed (expressiveness more important now)

    # waste of space
    rm(user, 'profile_image_url')
    rm(user, 'entities')

    # public_metrics should always be defined.
    rm(user['public_metrics'], 'listed_count')

    # does not support the .000Z extension so, we remove it
    # fromisoformat is just intended to be the inverse of
    # datetime.isoformat().
    # we cast to int for some easy space saving, and to avoid screwing things up
    # later in serilization. (we don't record sub second level accuracy)
    user['created_at'] = int(datetime.fromisoformat(user['created_at'][:-5]).timestamp())

    # flatten public_metrics
    for k, v in user['public_metrics'].items():
        user[k] = v
    del user['public_metrics']


    return user


def process(users, userids, tweet):
    for user in tweet['includes']['users']:
        uid = int(user['id'])

        if uid not in userids:
            users.append(compress(user))
            userids.add(uid)

    if len(users) > SAVE_EVERY:
        serialize_users(users)
        users.clear()



print(json.dumps(SCHEMA)) # dump the header at the top of the file
tweets = 0
while True:
    tweets += 1
    log(f'tweets: {tweets} users: {len(userids)}')
    try:
        tweet = json.loads(input())
        process(users, userids, tweet)

    except (json.JSONDecodeError, IndexError) as e:
        log(e)

