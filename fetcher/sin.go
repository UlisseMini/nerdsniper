package main

import (
	"database/sql"
	"errors"
	"strconv"

	"github.com/lib/pq"
)

var errIDParse = errors.New("failed to parse id")

// MUST STAY IN SYNC with ./db.sql
// todo: go generate this?
var userColumns = []string{ // constant
	"id", "name", "username", "url", "description",
	"location", "created_at", "pinned_tweet_id", "protected", "verified",
	"followers_count", "following_count", "tweet_count",

	"tweets",
}

var tweetColumns = []string{ // constant
	"text", "id", "author_id", "created_at", "in_reply_to_user_id", "lang",
	"retweet_count", "reply_count", "like_count", "quote_count",
	"possibly_sensitive", "conversation_id", "source",
}

////////////////////////////////////// BEGIN SIN ////////////////////////////////////////////////
// "you're too dumb for generics, bitch" - the go team
// ok then, I guess my vim skills are gonna pay of *copy paste intensifies*
// for real, i could maybe *maybe* rewrite this with closures. I'll do that later (maybe)

func addUsers(db *sql.DB, users []User) error {
	// 1. check duplicates

	userids := useridsFromUsers(users)

	dups, err := duplicates(db, "users", userids)
	users = removeDuplicateUsers(dups, users)

	// 2. add users which are not duplicates
	txn, err := db.Begin()
	if err != nil {
		return err
	}

	stmt, err := txn.Prepare(pq.CopyIn("users", userColumns...))
	if err != nil {
		return err
	}

	for _, user := range users {
		values, err := dbUser(user)
		if err != nil {
			continue
		}

		_, err = stmt.Exec(values...)

		if err != nil {
			return err
		}
	}

	_, err = stmt.Exec()
	if err != nil {
		return err
	}

	err = stmt.Close()
	if err != nil {
		return err
	}

	return txn.Commit()

}

func dbUser(user User) (values []interface{}, err error) {
	if user.id == 0 {
		return nil, errIDParse
	}

	pinnedTweetID := sql.NullInt64{}
	pinnedTweetID.Int64, err = strconv.ParseInt(user.PinnedTweetID, 10, 64)
	pinnedTweetID.Valid = err == nil

	return []interface{}{
		user.id, user.Name, user.Username, user.URL, user.Description,

		user.Location, user.CreatedAt, pinnedTweetID, user.Protected, user.Verified,
		user.PublicMetrics.FollowersCount, user.PublicMetrics.FollowingCount, user.PublicMetrics.TweetCount,

		pq.Array([]int64{}),
	}, nil
}

func removeDuplicateUsers(dups map[int64]bool, ids []User) []User {
	i := 0 // output index
	for _, id := range ids {
		if !dups[id.id] {
			ids[i] = id
			i++

			// if the user shows up again, they are a duplicate.
			// we need this since users can post comments on their own tweets.
			dups[id.id] = true
		}
	}

	// if this leaks memory i'm suing google
	// log.Printf("ids before: %#v", useridsFromUsers(ids))
	ids = ids[:i]
	// log.Printf("ids after: %#v", useridsFromUsers(ids))
	// log.Printf("dups: %#v", dups)
	return ids
}

func useridsFromUsers(users []User) []int64 {
	userids := make([]int64, len(users))
	for _, user := range users {
		userids = append(userids, user.id)
	}
	return userids
}

func addTweets(db *sql.DB, tweets []Tweet) error {
	// 1. check duplicates

	tweetids := tweetidsFromTweets(tweets)

	dups, err := duplicates(db, "tweets", tweetids)
	tweets = removeDuplicateTweets(dups, tweets)

	// 2. add tweets which are not duplicates
	txn, err := db.Begin()
	if err != nil {
		return err
	}

	stmt, err := txn.Prepare(pq.CopyIn("tweets", tweetColumns...))
	if err != nil {
		return err
	}

	for _, tweet := range tweets {
		values, err := dbTweet(tweet)
		if err != nil {
			continue
		}

		_, err = stmt.Exec(values...)

		if err != nil {
			return err
		}
	}

	_, err = stmt.Exec()
	if err != nil {
		return err
	}

	err = stmt.Close()
	if err != nil {
		return err
	}

	return txn.Commit()

}

func dbTweet(t Tweet) (values []interface{}, err error) {
	if t.id == 0 {
		return nil, errIDParse
	}

	return []interface{}{
		t.Text,
		t.id,
		t.AuthorID,
		t.CreatedAt,
		parseID(t.InReplyToUserID),
		t.Lang,
		t.PublicMetrics.RetweetCount,
		t.PublicMetrics.ReplyCount,
		t.PublicMetrics.LikeCount,
		t.PublicMetrics.QuoteCount,
		t.PossiblySensitive,
		t.ConversationID,
		t.Source,
	}, nil
}

func removeDuplicateTweets(dups map[int64]bool, ids []Tweet) []Tweet {
	i := 0 // output index
	for _, id := range ids {
		if !dups[id.id] {
			ids[i] = id
			i++

			// if the user shows up again, they are a duplicate.
			// we need this since users can post comments on their own tweets.
			dups[id.id] = true
		}
	}

	// if this leaks memory i'm suing google
	// log.Printf("ids before: %#v", tweetidsFromTweets(ids))
	ids = ids[:i]
	// log.Printf("ids after: %#v", tweetidsFromTweets(ids))
	// log.Printf("dups: %#v", dups)
	return ids
}

func tweetidsFromTweets(tweets []Tweet) []int64 {
	tweetids := make([]int64, len(tweets))
	for _, tweet := range tweets {
		tweetids = append(tweetids, tweet.id)
	}
	return tweetids
}

////////////////////////////////////// END SIN ////////////////////////////////////////////////
