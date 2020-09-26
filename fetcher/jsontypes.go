package main

import "time"

// TweetTopLevel ...
type TweetTopLevel struct {
	Data     Data     `json:"data"`
	Includes Includes `json:"includes"`
}

// ReferencedTweets ...
type ReferencedTweets struct {
	Type string `json:"type"`
	ID   string `json:"id"`
}

// PublicMetricsTweet ...
type PublicMetricsTweet struct {
	RetweetCount int `json:"retweet_count"`
	ReplyCount   int `json:"reply_count"`
	LikeCount    int `json:"like_count"`
	QuoteCount   int `json:"quote_count"`
}

// Mentions ...
type Mentions struct {
	Start    int    `json:"start"`
	End      int    `json:"end"`
	Username string `json:"username"`
}

// Data ...
type Data struct {
	Source            string             `json:"source"`
	ReferencedTweets  []ReferencedTweets `json:"referenced_tweets"`
	InReplyToUserID   string             `json:"in_reply_to_user_id"`
	CreatedAt         time.Time          `json:"created_at"`
	PossiblySensitive bool               `json:"possibly_sensitive"`
	Text              string             `json:"text"`
	AuthorID          string             `json:"author_id"`
	PublicMetrics     PublicMetricsTweet `json:"public_metrics"`
	Lang              string             `json:"lang"`
	ConversationID    string             `json:"conversation_id"`
	ID                string             `json:"id"`
}

func (d Data) asTweet() Tweet {
	return Tweet{
		d.Source,
		d.CreatedAt,
		d.PossiblySensitive,
		d.Text,
		d.AuthorID,
		d.PublicMetrics,
		d.Lang,
		d.ConversationID,
		d.ID,
	}

}

// PublicMetricsUser ...
type PublicMetricsUser struct {
	FollowersCount int `json:"followers_count"`
	FollowingCount int `json:"following_count"`
	TweetCount     int `json:"tweet_count"`
	ListedCount    int `json:"listed_count"`
}

// Urls ...
type Urls struct {
	Start       int    `json:"start"`
	End         int    `json:"end"`
	URL         string `json:"url"`
	ExpandedURL string `json:"expanded_url"`
	DisplayURL  string `json:"display_url"`
}

// URL ...
type URL struct {
	Urls []Urls `json:"urls"`
}

// User ...
type User struct {
	Name            string            `json:"name"`
	Verified        bool              `json:"verified"`
	Location        string            `json:"location"`
	ProfileImageURL string            `json:"profile_image_url"`
	ID              string            `json:"id"`
	id              int64             // we parse ID to int64 in code.
	URL             string            `json:"url"`
	PinnedTweetID   string            `json:"pinned_tweet_id"`
	CreatedAt       time.Time         `json:"created_at"`
	PublicMetrics   PublicMetricsUser `json:"public_metrics"`
	Description     string            `json:"description"`
	Username        string            `json:"username"`
	Protected       bool              `json:"protected"`
}

// Tweet ...
type Tweet struct {
	Source            string             `json:"source"`
	CreatedAt         time.Time          `json:"created_at"`
	PossiblySensitive bool               `json:"possibly_sensitive"`
	Text              string             `json:"text"`
	AuthorID          string             `json:"author_id"`
	PublicMetrics     PublicMetricsTweet `json:"public_metrics"`
	Lang              string             `json:"lang"`
	ConversationID    string             `json:"conversation_id"`
	ID                string             `json:"id"`
}

// Includes ...
type Includes struct {
	Users  []User  `json:"users"`
	Tweets []Tweet `json:"tweets"`
}
