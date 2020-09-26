-- WHEN YOU CHANGE THIS YOU MUST ALSO CHANGE userColumns IN main.go
-- AND stmt.Exec() IN main.go
-- (I should really use code generation some time...)
CREATE TABLE users (
	-- userobject fields we want
	id bigint,
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
	tweet_count int,

	-- the users tweets, an array of tweet id
	tweets bigint[]
);

CREATE TABLE tweets (
	text varchar,
	id bigint,
	author_id bigint,
	created_at varchar,
	in_reply_to_user_id bigint,
	lang varchar,
	retweet_count integer,
	reply_count integer,
	like_count integer,
	quote_count integer,
	possibly_sensitive boolean,
	conversation_id bigint,
	source varchar
);

CREATE UNIQUE INDEX userids ON users (id);
CREATE UNIQUE INDEX tweetids ON tweets (id);

-- Indexes are automatically used when available
-- SELECT id FROM users WHERE id IN (1,2,3);
