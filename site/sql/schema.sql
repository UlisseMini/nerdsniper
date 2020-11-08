CREATE TABLE tweets (
    text character varying,
    id bigint,
    author_id bigint,
    created_at character varying,
    in_reply_to_user_id bigint,
    lang character varying,
    retweet_count integer,
    reply_count integer,
    like_count integer,
    quote_count integer,
    possibly_sensitive boolean,
    conversation_id bigint,
    source character varying
);

CREATE TABLE users (
    id bigint,
    name character varying,
    username character varying,
    url character varying,
    description character varying,
    location character varying,
    created_at timestamp without time zone,
    pinned_tweet_id bigint,
    protected boolean,
    verified boolean,
    followers_count integer,
    following_count integer,
    tweet_count integer,
    lang character varying,
    textsearchable tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig, (description)::text)) STORED
);


/*
* NOTE: If you have an ssd and a disk, you should create a tablespace on the ssd for these,
* VERY important we have fast read throughput for indexing.
*/

CREATE        INDEX textsearchable_idx ON users  USING gin   (textsearchable);
CREATE UNIQUE INDEX tweet_ids          ON tweets USING btree (id);
CREATE        INDEX author_ids         ON tweets USING btree (author_id);
CREATE UNIQUE INDEX userids            ON users  USING btree (id);

