package main

import (
	"bufio"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"time"

	"strconv"

	"github.com/lib/pq"
)

var params = url.Values{

	"expansions":   {"author_id,entities.mentions.username,geo.place_id,in_reply_to_user_id,referenced_tweets.id,referenced_tweets.id.author_id"},
	"tweet.fields": {"attachments,author_id,context_annotations,conversation_id,created_at,entities,geo,id,in_reply_to_user_id,lang,public_metrics,possibly_sensitive,referenced_tweets,source,text,withheld"},
	"user.fields":  {"created_at,description,entities,id,location,name,pinned_tweet_id,profile_image_url,protected,public_metrics,url,username,verified,withheld"},

	// Trying not to be a whore...
	// "media.fields": {"duration_ms,height,media_key,preview_image_url,type,url,width,public_metrics"},
	// "place.fields": {"contained_within,country,country_code,full_name,geo,id,name,place_type"},
	// "poll.fields":  {"duration_minutes,end_datetime,id,options,voting_status"},
}

var (
	errUnauthorized = errors.New("unauthorized")
	errStatus       = errors.New("bad status")
)

func init() {
	log.SetFlags(log.Lshortfile) // TODO: add time
}

func tweetsRequest(client http.Client, bearer string) (*http.Response, error) {
	headers := http.Header{"Authorization": {"Bearer " + bearer}}

	u, err := url.Parse("https://api.twitter.com/2/tweets/sample/stream")
	if err != nil {
		log.Fatal(err) // unreachable, static url is parsable ^
	}
	values := u.Query()
	for k, p := range params {
		values.Add(k, p[0])
	}
	u.RawQuery = values.Encode()

	req := &http.Request{
		Method: "GET",
		URL:    u,
		Header: headers,
	}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode != 200 {
		switch resp.StatusCode {
		case 401:
			return nil, errUnauthorized

		default:
			log.Printf("bad status: %d\n", resp.StatusCode)
			return nil, errStatus
		}
	}

	return resp, err

}

func tweets(client http.Client, bearer string) <-chan TweetTopLevel {
	c := make(chan TweetTopLevel)

	go func() {
		for {
			resp, err := tweetsRequest(client, bearer)
			if err != nil {
				log.Print(err)
				break
			}

			s := bufio.NewScanner(resp.Body)
			for s.Scan() {
				t := TweetTopLevel{}

				err := json.Unmarshal(s.Bytes(), &t)
				if err != nil {
					fmt.Fprintf(os.Stderr, "Failed json parse: %v\n", err)
					continue
				}

				c <- t
			}

			resp.Body.Close()
		}

		// Retry in 10s
		time.Sleep(time.Second * 10)
	}()

	return c
}

const (
	host   = "localhost"
	port   = 5432
	user   = "postgres"
	dbname = "postgres"
)

func connectToDB() (*sql.DB, error) {
	password := getenv("DB_PASSWORD")

	psqlconn := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable", host, port, user, password, dbname)

	return sql.Open("postgres", psqlconn)

}

func duplicates(db *sql.DB, userids []int64) (map[int64]bool, error) {
	query := `SELECT id FROM users WHERE id = ANY($1)`
	rows, err := db.Query(query, pq.Array(userids))
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	// not the most space efficent but who cares, we'll only be doing this in
	// small batches.
	dups := make(map[int64]bool)

	for rows.Next() {
		var id int64
		err = rows.Scan(&id)
		if err != nil {
			return nil, err
		}

		dups[id] = true
	}

	return dups, nil
}

func removeDuplicates(dups map[int64]bool, users []User) []User {
	i := 0 // output index
	for _, user := range users {
		if !dups[user.id] {
			users[i] = user
			i++

			// if the user shows up again, they are a duplicate.
			// we need this since users can post comments on their own tweets.
			dups[user.id] = true
		}
	}

	// if this leaks memory i'm suing google
	log.Printf("users before: %#v", useridsFromUsers(users))
	users = users[:i]
	log.Printf("users after: %#v", useridsFromUsers(users))
	log.Printf("dups: %#v", dups)
	return users
}

// userColumns MUST STAY IN SYNC with ./db.sql
// todo: go generate this?
var userColumns = []string{ // constant
	"id", "name", "username", "url", "description",
	"location", "created_at", "pinned_tweet_id", "protected", "verified",
	"followers_count", "following_count", "tweet_count",

	"tweets",
}

func dbUser(user User) (values []interface{}, err error) {
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

func addUsers(db *sql.DB, users []User) error {
	// 1. check duplicates

	userids := useridsFromUsers(users)

	dups, err := duplicates(db, userids)
	users = removeDuplicates(dups, users)

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
			log.Printf("%s", err)
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

func addTweets(db *sql.DB, tweets []Tweet) error {
	return nil
}

func main() {
	db, err := connectToDB()
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	err = db.Ping()
	if err != nil {
		log.Fatal(err)
	}
	log.Printf("Connected to %s@%s:%d/%s", user, host, port, dbname)

	bearer := getenv("BEARER_TOKEN")
	client := http.Client{}
	gen := tweets(client, bearer)
	for tweet := range gen {
		start := time.Now()

		var tweets []Tweet
		tweets = append(tweets, tweet.Data.asTweet())
		for _, tweet := range tweet.Includes.Tweets {
			tweets = append(tweets, tweet)
		}

		if err := addTweets(db, tweets); err != nil {
			log.Fatal(err)
		}

		var users []User

		for _, user := range tweet.Includes.Users {
			user.id, err = strconv.ParseInt(user.ID, 10, 64)
			if err == nil && user.id != 0 {
				users = append(users, user)
			}
		}

		if err := addUsers(db, users); err != nil {
			log.Fatal(err)
		}

		log.Printf("tweet processing took %s", time.Since(start))
	}

}

func getenv(name string) string {
	val := os.Getenv(name)
	if val == "" {
		log.Fatalf("env-var $%s is unset", name)
	}
	return val
}

func useridsFromUsers(users []User) []int64 {
	userids := make([]int64, len(users))
	for _, user := range users {
		userids = append(userids, user.id)
	}
	return userids
}
