from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import time

import asyncpg as pg

# TODO: DDOS, I mean benchmark

app = FastAPI()


SEARCH_SQL = '''
SELECT username, name, description
FROM users
WHERE textsearchable @@ plainto_tsquery($1)
LIMIT 100
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


@app.get('/search', response_class=HTMLResponse)
async def search(request: Request, q: str):
    global timings

    start = time.time()
    async with pool.acquire() as conn:
        values = await conn.fetch(SEARCH_SQL, q)
    timings['db'] += time.time() - start


    start = time.time()
    rendered = templates.TemplateResponse('search.html', {
        'users': values,
        'request': request,
        'search': q,
    })
    timings['jinja'] += time.time() - start

    return rendered


@app.get('/api/timings')
async def timings_api():
    global timings
    return timings

@app.get('/api/search')
async def search_api(q: str):
    async with pool.acquire() as conn:
        values = await conn.fetch(SEARCH_SQL, q)
    return values


app.mount('/',  StaticFiles(directory='./static', html=True))

