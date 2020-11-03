/* NOTE: Before running this make sure there is an index on tweets.author_id, otherwise it will never finish! */

ALTER TABLE users
ADD COLUMN lang char(2);

/* Or if it exists... */
/* ALTER TABLE users ALTER COLUMN TYPE varchar(3); */

UPDATE users
SET
	lang = (
		SELECT lang
		FROM tweets WHERE author_id=users.id
		GROUP BY lang
		ORDER BY count(lang) desc
		LIMIT 1
	)
WHERE
	lang IS NULL;
