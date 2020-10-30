from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import random
import time
import os
from queryparser import parse_query, ParseError
import queryparser

import asyncpg as pg

# TODO: DDOS, I mean benchmark

app = FastAPI()

MOTTOS = [
    "when you don't have friends, snipe them",
    "because we're all so alone",
    "privacy is dead",
    "i profit from your loneliness",
    "the home of friendly cyberstalkers"
]

templates = Jinja2Templates(directory="templates")

timings = {
    'db': 0,
    'jinja': 0,
}

@app.on_event('startup')
async def startup():
    global pool
    pool = await pg.create_pool(
        user=os.environ['PG_USER'],
        password=os.environ['PG_PASS'],
        database=os.environ['PG_DB'],
    )


@app.on_event('shutdown')
async def shutdown():
    await pool.close()


async def search(q: str):
    print('search', q)
    sql, args = parse_query(q)

    print(sql, args)

    async with pool.acquire() as conn:
        values = await conn.fetch(sql, *args)

    return values


@app.get('/search', response_class=HTMLResponse)
async def search_html(request: Request, q: str):
    global timings

    start = time.time()
    values = []
    err = ""
    try:
        values = await search(q)
    except ParseError as e:
        print(e)
        err = str(e)

    timings['db'] += time.time() - start

    start = time.time()
    rendered = templates.TemplateResponse('search.html', {
        'users': values,
        'num_results': len(values),
        'request': request,
        'motto': random.choice(MOTTOS),
        'search': q,
        'err': err,
    })
    timings['jinja'] += time.time() - start

    return rendered



@app.get('/api/search')
async def search_api(q: str):
    return await search(q)


@app.get('/api/timings')
async def timings_api():
    global timings
    return timings


@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('home.html', {
        'motto': random.choice(MOTTOS),
        'docs': queryparser.docs,
        'request': request,
    })



@app.get('/about', response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse('about.html', {
        'request': request,
    })


app.mount('/',  StaticFiles(directory='./static'))

