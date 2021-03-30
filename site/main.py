from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import random
import os
from queryparser import parse_query, ParseError
import queryparser

import asyncpg as pg

app = FastAPI()

MOTTOS = [
    "the twitter search engine",
    "when you don't have friends, snipe them",
    "because we're all so alone",
    "privacy is dead",
    "the home of friendly cyberstalkers",
    "this is how zucc feels"
]

templates = Jinja2Templates(directory="templates")

@app.on_event('startup')
async def startup():
    global pool
    pool = await pg.create_pool(
        user=os.environ.get('PG_USER')     or 'postgres',
        password=os.environ.get('PG_PASS') or 'postgres',
        database=os.environ.get('PG_DB')   or 'postgres',
    )


@app.on_event('shutdown')
async def shutdown():
    await pool.close()


def get_motto(request: Request):
    # basic SEO; show MOTTOS[0] when crawler
    h = request.headers.get('user-agent')
    if h is not None and 'bot' in h.lower():
        return MOTTOS[0]
    else:
        return random.choice(MOTTOS)



async def search(q: str):
    print('search', q)
    sql, args = parse_query(q)

    print(sql, args)

    async with pool.acquire() as conn:
        values = await conn.fetch(sql, *args)

    return values



@app.get('/search', response_class=HTMLResponse)
async def search_html(request: Request, q: str):
    values = []
    err = ""
    try:
        values = await search(q)
    except ParseError as e:
        print(e)
        err = str(e)



    rendered = templates.TemplateResponse('search.html', {
        'users': values,
        'num_results': len(values),
        'request': request,
        'motto': get_motto(request),
        'search': q,
        'err': err,
    })

    return rendered



@app.get('/api/search')
async def search_api(q: str):
    return await search(q)


@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('home.html', {
        'motto': get_motto(request),
        'docs': queryparser.docs,
        'request': request,
    })



@app.get('/about', response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse('about.html', {
        'request': request,
    })


app.mount('/',  StaticFiles(directory='./static'))

