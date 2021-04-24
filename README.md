# nerdsniper

This is a project to try searching twitter data based on inferring stuff about users from their tweets,

I was going to do graph theory stuff on followers/following data, but the twitter api doesn't let me fetch these in bulk.
even with 100 api tokens it would take over a year to fetch all of twitter.

I thought about instead being tweet-centric by using the `tweets/stream` endpoint (which I was already doing to fetch users quickly)
but then it quickly turned into [twitter search](https://twitter.com/search).

Maybe only fetching following data from popular accounts (ie. elonmusk, snowden) would work,
then I can use many api requests to figure out what popular accounts are about.

The problem with that is I get a lot of inactive accounts. I don't have the storage capacity for that.
I could slow down slurping of followers to meet the limits of the timeline api, but then I'd be limited to 100 users/min.
Might still be feasible with user auth, If I incentivize people to login \w twitter on nerdsniper.



