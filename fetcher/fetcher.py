"""
Fetch tweets from twitter. Send over tcp://127.0.0.1:1234
(we don't use ncat beacuse if the archiver goes down, we need to retry,
 and i'm not far gone enough to use a shell while loop with return codes)
"""

import requests
import json
import socket
import os
import time

PARAMS = {
    "expansions": "attachments.poll_ids,attachments.media_keys,author_id,entities.mentions.username,geo.place_id,in_reply_to_user_id,referenced_tweets.id,referenced_tweets.id.author_id",
    "media.fields": "duration_ms,height,media_key,preview_image_url,type,url,width,public_metrics",
    "place.fields": "contained_within,country,country_code,full_name,geo,id,name,place_type",
    "poll.fields": "duration_minutes,end_datetime,id,options,voting_status",
    "tweet.fields": "attachments,author_id,context_annotations,conversation_id,created_at,entities,geo,id,in_reply_to_user_id,lang,public_metrics,possibly_sensitive,referenced_tweets,source,text,withheld",
    "user.fields": "created_at,description,entities,id,location,name,pinned_tweet_id,profile_image_url,protected,public_metrics,url,username,verified,withheld",
}


def tweets(bearer, params=PARAMS):
    "Generator of tweets. from /tweets/sample/stream endpoint."
    with requests.get(
        "https://api.twitter.com/2/tweets/sample/stream",
        headers={"Authorization": f"Bearer {bearer}"},
        params=params,
        stream=True,
    ) as stream:
        for line in stream.iter_lines():
            if line:
                try:
                    yield json.loads(line)
                except json.decoder.JSONDecodeError:
                    pass


def handle(s, tweet):
    s.sendall(json.dumps(tweet).encode() + b'\n')


bearer = os.environ['BEARER_TOKEN']
while True:
    try:
        s = socket.socket()
        s.connect(('localhost', 1234))
        s.setblocking(False)
        print('Connected.')

        for tweet in tweets(bearer):
            handle(s, tweet)

    except Exception as e:
        print(e)
        print('Waiting 10s with the hopes of the big bad error going away...')


    time.sleep(10)
