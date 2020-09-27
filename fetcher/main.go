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
	"strings"
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

	u, _ := url.Parse("https://api.twitter.com/2/tweets/sample/stream")
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

func tweetsDaemon(client http.Client, bearer string, c chan<- TweetTopLevel) {
	resp, err := tweetsRequest(client, bearer)
	if err != nil {
		log.Print(err)
		return
	}
	defer resp.Body.Close()
	log.Printf("connected to twitter API")

	s := bufio.NewScanner(resp.Body)
	for s.Scan() {
		if strings.TrimSpace(s.Text()) == "" {
			continue
		}

		t := TweetTopLevel{}

		err := json.Unmarshal(s.Bytes(), &t)
		if err != nil {
			log.Printf("Failed json parse: %v\n", err)
			log.Printf("json: %s", s.Bytes())

			continue
		}

		c <- t
	}
}

func tweets(client http.Client, bearer string) <-chan TweetTopLevel {
	c := make(chan TweetTopLevel)

	go func() {
		for {
			tweetsDaemon(client, bearer, c)

			// Retry every 10s
			time.Sleep(time.Second * 10)
		}
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

func duplicates(db *sql.DB, table string, ids []int64) (map[int64]bool, error) {
	// table is not user supplied, so this is safe. (and I don't think $1 would work with a table)
	query := fmt.Sprintf(`SELECT id FROM %s WHERE id = ANY($1)`, table)

	rows, err := db.Query(query, pq.Array(ids))
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

func tweetsMult(client http.Client, bearers []string) <-chan TweetTopLevel {
	c := make(chan TweetTopLevel)

	for _, bearer := range bearers {
		go func(bearer string) {
			for t := range tweets(client, bearer) {
				c <- t
			}
		}(bearer)
	}

	return c
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

	bearers := strings.Split(getenv("BEARER_TOKENS"), ",")

	client := http.Client{}
	gen := tweetsMult(client, bearers)

	numTweets := 0
	numUsers := 0
	numIter := 0

	for tweet := range gen {
		if numIter%1000 == 0 {
			log.Printf("tweet_toplevel: %d, users: %d tweets: %d", numIter, numUsers, numTweets)
		}

		var tweets []Tweet
		tweets = append(tweets, tweet.Data.asTweet())
		for _, tweet := range tweet.Includes.Tweets {
			tweet.id = parseID(tweet.ID)

			// ignore tweets where parsing id failed.
			if tweet.id != 0 {
				tweets = append(tweets, tweet)
			}

		}

		if err := addTweets(db, tweets); err != nil {
			log.Fatal(err)
		}

		var users []User

		for _, user := range tweet.Includes.Users {
			user.id = parseID(user.ID)
			// ignore users where parsing id failed.
			if user.id != 0 {
				users = append(users, user)
			}
		}

		if err := addUsers(db, users); err != nil {
			log.Fatal(err)
		}

		numTweets += len(tweets)
		numUsers += len(users)
		numIter++
	}

}

func getenv(name string) string {
	val := os.Getenv(name)
	if val == "" {
		log.Fatalf("env-var $%s is unset", name)
	}
	return val
}

func parseID(id string) int64 {
	num, _ := strconv.ParseInt(id, 10, 64)
	return num
}
