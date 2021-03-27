
There are two approaches for fetching from the twitter api

## Bulk
Using [tweets/sampled-stream](https://developer.twitter.com/en/docs/twitter-api/tweets/sampled-stream/introduction)

Pros:
- Extremely fast
- Only get users who tweet (active users)

Cons:
- No followers/following data, so no graphs
- Small amount of users tweet tons so becomes less efficent
- Parrallelize might not work if twitter gives the same sample to everyone
- Retweet bias (my data shows 32.3% of bulk are retweets)

## Spider

Using [get-users](https://developer.twitter.com/en/docs/twitter-api/users/lookup/api-reference/get-users) and [follows](https://developer.twitter.com/en/docs/twitter-api/users/follows/introduction)

We could spider through users based on their friends, this gives rich graph data for analysis but will be slower, it can be parrallelized though.

Pros:
- Rich graph data
- Can be made parallel easily

Cons:
- Inactive accounts get stored

## Hybrid

Get users in bulk, then get who they following.
Avg number of people followed is 500 for people in the bulk stream. so 4bytes/id gives avg of 2kb/user in followers. totally doable!

```sql
select AVG(following_count) from users where following_count < 5000;
469.1591892948627418

select avg(followers_count) from users where followers_count < 5000;
416.5171619425835110
```

Rough data size estimate per user
```py
bpu = 0 # bytes per user
bpu += 2000 # following
bpu += 2000 # followers
bpu += 30   # bio
bpu += 30   # metadata

free = 6e10 # 60gb
print(free / bpu) # 15m users can be stored in 60GB
print(1e9 / bpu)  # ~250k users can be stored in 1GB
```


Pros:
- No inactive accounts since they are from the bulk stream
- Rich followers/following data :D

Cons:
- Less accounts can be supported

