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


# page_ptr is the largest index from the previous page.
async def search(q: str, page_ptr: int):
    async with pool.acquire() as conn:
        values = await conn.fetch(SEARCH_SQL, q, page_ptr, PAGE_SIZE)
    return values


@app.get('/search', response_class=HTMLResponse)
async def search_html(request: Request, q: str, ptr: int = 0):
    global timings

    start = time.time()
    values = await search(q, ptr)
    timings['db'] += time.time() - start

    page_ptr = values[-1]['id']

    start = time.time()
    rendered = templates.TemplateResponse('search.html', {
        'users': values,
        'num_results': len(values),
        'PAGE_SIZE': PAGE_SIZE,
        'request': request,
        'motto': random.choice(MOTTOS),
        'search': q,
        'ptr': page_ptr,
    })
    timings['jinja'] += time.time() - start

    return rendered



@app.get('/api/search')
async def search_api(q: str, ptr: int = 0):
    return await search(q, page, ptr)


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

