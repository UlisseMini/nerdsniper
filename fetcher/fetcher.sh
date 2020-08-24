#!/bin/sh

if [ -z "$BEARER_TOKEN" ]; then
	echo "Please provide \$BEARER_TOKEN"
	exit 1
fi

# NOTE: Make sure if you add something here you update both!
FIELDS="author_id,created_at,in_reply_to_user_id,lang,public_metrics,possibly_sensitive,conversation_id,source"
JQ_CSV=".author_id, .created_at, .in_reply_to_user_id, .lang, .public_metrics[], .possibly_sensitive, .conversation_id, .source"

while true; do
	echo "Connecting to stream..." 1>&2
	curl -sSL -X GET -H \
		"Authorization: Bearer $BEARER_TOKEN" \
		"https://api.twitter.com/2/tweets/sample/stream?tweet.fields=$FIELDS" \
		| jq -r ".data | [$JQ_CSV] | @csv"
		# | jq -r ".data"

	echo "curl error: $?, waiting 10s..." 1>&2
	sleep 10
done
