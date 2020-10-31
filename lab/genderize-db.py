import pandas as pd
import time

print('Reading data')

F = pd.read_csv('results/female.csv')
M = pd.read_csv('results/male.csv')
print(len(F)/(len(F) + len(M)))


# Fix gender distributions in data. This is silly; batching might work better.
print('Fixing ratios')
s = min(len(F), len(M))

F = F[:s]
M = M[:s]

def tokenize(s):
    tokens = []

    s = s.strip().lower()

    s = s.replace('she/her', '')
    s = s.replace('he/him', '')

    for char in ',.:();|':
        s = s.replace(char, '')

    for char in '/\n':
        s = s.replace(char, ' ')



    ignore_words = {'a', 'and', 'it', }

    tokens += list(filter(
        lambda t: t != '' and t not in ignore_words,
        map(str.strip, s.split(' '))
    ))



    return tokens

def populate(token_freq_dict, df):
    for desc in df.description:
        for token in tokenize(desc):
            token_freq_dict[token] = (token_freq_dict.get(token) or 0) + 1


    return token_freq_dict



token_freqs_F = populate({}, F)
token_freqs_M = populate({}, M)

def delete(d, k):
    try:
        del d[k]
    except KeyError:
        pass


# Only keep words with more then 1000 total occurences to avoid skewing
for token in set([*token_freqs_F.keys(), *token_freqs_M.keys()]):
    total = (token_freqs_F.get(token) or 0) + (token_freqs_M.get(token) or 0)
    if total < 100:
        delete(token_freqs_F, token)
        delete(token_freqs_M, token)
        #tf_F_small[token] = token_freqs_F.get(token) or 0
        #tf_M_small[token] = token_freqs_M.get(token) or 0



print('min F', min(token_freqs_F.values()))
print('len F', len(token_freqs_F))
print('min M', min(token_freqs_M.values()))
print('len M', len(token_freqs_M))


tokens_in_F = sum(token_freqs_F.values())
tokens_in_M = sum(token_freqs_M.values())

print(tokens_in_F)
print(tokens_in_M)


def P_female_given(tokens):
    P_H = 0.5

    for token in tokens:
        if token_freqs_F.get(token) is None or token_freqs_M.get(token) is None:
            continue

        # P(H)P(E|H) / P(H)P(E|H) + P(-H)P(E|-H)
        P_E_GIVEN_H      = token_freqs_F[token] / tokens_in_F
        P_E_GIVEN_NULL_H = token_freqs_M[token] / tokens_in_M

        P_NULL_H = 1 - P_H
        P_H = (P_H*P_E_GIVEN_H) / (P_H*P_E_GIVEN_H + P_NULL_H*P_E_GIVEN_NULL_H)

    return P_H



# Time to update the database.

import asyncio
import asyncpg as pg
import os

# Strategy:

async def main():
    pool = await pg.create_pool(
        user=os.environ['PG_USER'],
        password=os.environ['PG_PASS'],
        database=os.environ['PG_DB'],
    )

    # splitting this into multiple async coroutines
    # with buffering would be a bit faster I think
    async with pool.acquire() as conn:
        total = 0
        batch_s = 1000
        while True:
            async with conn.transaction():
                i = 0

                batch = []
                print('read ', flush=True, end='')
                async for record in conn.cursor(
                    f'SELECT id, description FROM users WHERE P_female IS NULL LIMIT {batch_s}'
                ):

                    bio = record['description']
                    tokens = tokenize(bio)
                    p = P_female_given(tokens)

                    batch.append((p, record['id']))
                    i += 1


                print('update ', end='', flush=True)
                # batch update from batch
                await conn.executemany(
                    'UPDATE users SET P_female = $1 WHERE id=$2',
                    batch
                )

                total += i
                print(total)

                if i < 1000:
                    break





if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
