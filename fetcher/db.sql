CREATE TABLE users (
	id bigint PRIMARY KEY,
	name varchar,
	username varchar,
	url varchar,
	description varchar,
	location varchar,

	created_at timestamp,
	pinned_tweet_id bigint,
	protected boolean,
	verified boolean,

	followers_count int,
	following_count int,
	tweet_count int
);

CREATE TABLE tweets (
	id                  bigint PRIMARY KEY,
	text                varchar,
	author_id           bigint,
	created_at          timestamp,
	in_reply_to_user_id bigint,
	-- we only store english tweets.
	-- lang                varchar,
	retweet_count       integer,
	reply_count         integer,
	like_count          integer,
	quote_count         integer,
	possibly_sensitive  boolean,
	conversation_id     bigint,
	source              varchar
);


CREATE TABLE following (
	userid bigint PRIMARY KEY,
	following bigint[]
);

CREATE TABLE followers (
	userid bigint PRIMARY KEY,
	followers bigint[]
);

-- Null index so fetcher can update null users with their following/followers :D
CREATE INDEX following_idx ON following (following) WHERE following IS NULL;
CREATE INDEX followers_idx ON followers (followers) WHERE followers IS NULL;


