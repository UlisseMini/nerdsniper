from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import random
import time

import asyncpg as pg

# TODO: DDOS, I mean benchmark

app = FastAPI()

# number of results per page.
PAGE_SIZE = 20

MOTTOS = [
    "when you don't have friends, snipe them",
    "because we're all so alone",
    "how many days till I feel something again?",
    "i profit from your loneliness",
    "the home of friendly cyberstalkers"
]

# n is serial.
# $2 is the largest id from the last page
# note: if you change asc to desc you must change search() aswell
# id+0 forces postgres to be big brained and use the index
# otherwise it would use a backward scan for some reason
SEARCH_SQL = f'''
SELECT id, username, name, description
FROM users
WHERE id > $2
AND textsearchable @@ plainto_tsquery($1)
ORDER BY id+0 asc
LIMIT $3
'''.strip()

templates = Jinja2Templates(directory="templates")

timings = {
    'db': 0,
    'jinja': 0,
}

@app.on_event('startup')
async def startup():
    global pool
    pool = await pg.create_pool(
        user='postgres',
        password='postgres',
        database='postgres',
    )


@app.on_event('shutdown')
async def shutdown():
    await pool.close()


# note: page is 1 indexed.
async def search(q: str, page: int):
    async with pool.acquire() as conn:
        # TODO: I could build a query depending on page size then
        # exec all this work on the db without comm overhead
        max_id = 0
        for _ in range(1, page):
            values = await conn.fetch(SEARCH_SQL, q, max_id, PAGE_SIZE)

            # if this page (before wanted page) has < PAGE_SIZE values
            # we can't have any for the next page.
            if len(values) < PAGE_SIZE:
                return []

            max_id = max(v['id'] for v in values)


        print(max_id)
        values = await conn.fetch(SEARCH_SQL, q, max_id, PAGE_SIZE)
    return values


@app.get('/search', response_class=HTMLResponse)
async def search_html(request: Request, q: str, page: int = 1):
    global timings

    start = time.time()
    values = await search(q, page)
    timings['db'] += time.time() - start


    start = time.time()
    rendered = templates.TemplateResponse('search.html', {
        'users': values,
        'page': page,
        'num_results': len(values),
        'PAGE_SIZE': PAGE_SIZE,
        'request': request,
        'motto': random.choice(MOTTOS),
        'search': q,
    })
    timings['jinja'] += time.time() - start

    return rendered



@app.get('/api/search')
async def search_api(q: str, page: int = 1):
    return await search(q, page)


@app.get('/api/timings')
async def timings_api():
    global timings
    return timings


@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('home.html', {
        'motto': random.choice(MOTTOS),
        'request': request,
    })


app.mount('/',  StaticFiles(directory='./static', html=True))

