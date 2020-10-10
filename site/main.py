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
PAGE_SIZE = 100

MOTTOS = [
    "when you don't have friends, snipe them",
    "because we're all so alone",
    "how many days till I feel something again?",
    "i profit from your loneliness",
    "the home of friendly cyberstalkers"
]

# id+0 forces postgres to be big brained and use the index
# otherwise it would use a backward scan for some reason
# TODO: would be nice to avoid the double compute for plainto_tsquery()
SEARCH_SQL = f'''
WITH results AS (
  SELECT id, username, name, description, textsearchable

  FROM users
  WHERE textsearchable @@ plainto_tsquery($1)
  LIMIT $2
)

SELECT id, username, name, description
FROM results
ORDER BY ts_rank(textsearchable, plainto_tsquery($1))
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


async def search(q: str):
    async with pool.acquire() as conn:
        values = await conn.fetch(SEARCH_SQL, q, PAGE_SIZE)
    return values


@app.get('/search', response_class=HTMLResponse)
async def search_html(request: Request, q: str):
    global timings

    start = time.time()
    values = await search(q)
    timings['db'] += time.time() - start

    start = time.time()
    rendered = templates.TemplateResponse('search.html', {
        'users': values,
        'num_results': len(values),
        'PAGE_SIZE': PAGE_SIZE,
        'request': request,
        'motto': random.choice(MOTTOS),
        'search': q,
    })
    timings['jinja'] += time.time() - start

    return rendered



@app.get('/api/search')
async def search_api(q: str):
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



@app.get('/about', response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse('about.html', {
        'request': request,
    })


app.mount('/',  StaticFiles(directory='./static'))

