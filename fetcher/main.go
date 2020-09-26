package main

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"os"
)

// TODO: Retry connection on disconect.
// TODO: Save tweets and users to csv
// TODO: Support N bearer tokens
// TODO: Proper Daemon with systemd
// TODO: Proper Daemon controls through socket OR signals and config file
// TODO?: Record entities

var params = url.Values{

	"expansions":   {"author_id,entities.mentions.username,geo.place_id,in_reply_to_user_id,referenced_tweets.id,referenced_tweets.id.author_id"},
	"tweet.fields": {"attachments,author_id,context_annotations,conversation_id,created_at,entities,geo,id,in_reply_to_user_id,lang,public_metrics,possibly_sensitive,referenced_tweets,source,text,withheld"},
	"user.fields":  {"created_at,description,entities,id,location,name,pinned_tweet_id,profile_image_url,protected,public_metrics,url,username,verified,withheld"},

	// Trying not to be a whore...
	// "media.fields": {"duration_ms,height,media_key,preview_image_url,type,url,width,public_metrics"},
	// "place.fields": {"contained_within,country,country_code,full_name,geo,id,name,place_type"},
	// "poll.fields":  {"duration_minutes,end_datetime,id,options,voting_status"},
}

var errUnauthorized = errors.New("unauthorized")

func tweetsRequest(client http.Client, bearer string) (*http.Response, error) {
	headers := http.Header{"Authorization": {"Bearer " + bearer}}

	u, err := url.Parse("https://api.twitter.com/2/tweets/sample/stream")
	if err != nil {
		panic(err)
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
			return nil, fmt.Errorf("bad status: %d", resp.StatusCode)
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
				panic(err)
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
	}()

	return c
}

func main() {
	bearer := os.Getenv("BEARER_TOKEN")

	client := http.Client{}
	gen := tweets(client, bearer)
	for tweet := range gen {
		fmt.Printf("created_at: %d\n", tweet.Data.CreatedAt.Unix())
	}

}
