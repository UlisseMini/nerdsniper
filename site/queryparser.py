SEARCH_SQL_TEMPLATE = '''
WITH results AS (
  SELECT id, username, name, description, textsearchable

  FROM users
  WHERE textsearchable @@ plainto_tsquery($1)
  {where}
  LIMIT {limit}
)

SELECT id, username, name, description
FROM results
ORDER BY ts_rank(textsearchable, plainto_tsquery($1))
'''.strip()

LIMIT = 100

class ParseError(Exception):
    pass


def parse_query(*args, **kwargs):
    try:
        return _parse_query(*args, **kwargs)
    except Exception as e:
        raise ParseError(repr(e))



def parse_gt_le(val):
    print(val)
    op = val[0]
    if op not in '><':
        raise ParseError('invalid operator: {} (valid are < and >)'.format(op))

    try:
        n = int(val[1:])
    except ValueError as e:
        raise ParseError('invalid integer: {}'.format(val[1:]))

    return op, n




# note: somewhat tollerable parser, if something *might* be a syntax error
# we let it through.
# we return (sql, args) where args is a list to be passed through asyncpg
# for serialization
def _parse_query(query: str) -> (str, str):
    sql = SEARCH_SQL_TEMPLATE

    where = ''
    query_raw = ''

    tokens = query.split(' ')
    for token in tokens:
        a = token.split(':')
        if len(a) != 2:
            query_raw += token
            continue


        stmt, val = a
        if stmt == 'followers':
            op, n = parse_gt_le(val)
            where += 'AND followers_count {} {}'.format(op, n)



    return sql.format(limit=LIMIT, where=where), [query_raw]
