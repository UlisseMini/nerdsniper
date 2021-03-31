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
	tweet_count int,

	-- gender ratio on twitter is ~0.3 female by default
	-- https://www.statista.com/statistics/828092/distribution-of-users-on-twitter-worldwide-gender/
	p_female numeric(2, 1) DEFAULT 0.3,

	textsearchable tsvector GENERATED ALWAYS AS (to_tsvector('english', description)) STORED
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

CREATE TABLE context_annotations (
	domain_id int,
	entity_id bigint,
	tweet_id bigint
);

CREATE INDEX context_annotations_tweet_id ON context_annotations (tweet_id);
CREATE INDEX context_annotations_domain_id ON context_annotations (domain_id);

-- Domain given in context_annotations, name for id
CREATE TABLE domain_names (
	domain_id int PRIMARY KEY,
	name varchar
);

-- Entity given in context annotations, name for id
CREATE TABLE entity_names (
	entity_id bigint PRIMARY KEY,
	name varchar
);


/* Followers / Following is infeasible
CREATE TABLE following (
	userid bigint PRIMARY KEY,
	following bigint[]
);

CREATE TABLE followers (
	userid bigint PRIMARY KEY,
	followers bigint[]
);

-- Null index so fetcher can update null users with their following/followers
CREATE INDEX following_idx ON following (following) WHERE following IS NULL;
CREATE INDEX followers_idx ON followers (followers) WHERE followers IS NULL;
*/
