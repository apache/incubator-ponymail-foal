#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Caching proxy for Gravatars"""

import plugins.server
import aiohttp
import aiohttp.web

CACHE_LIMIT = 25000  # Store a maximum of 25,000 gravatars in memory at any given time (25k x 5kb ≃125mb)
GRAVATAR_URL = "https://secure.gravatar.com/avatar/%s.png?s=96&r=g&d=mm"

gravatars = []
gravatar_cache = {}


async def fetch_gravatar(gid):
    headers = {"User-Agent": "Pony Mail Agent/0.1"}
    fetch_url = GRAVATAR_URL % gid
    # Fetch image and store internally
    try:
        async with aiohttp.client.request("GET", fetch_url, headers=headers) as rv:
            img_data = await rv.read()
            gravatars.append(gid)
            gravatar_cache[gid] = img_data
    except aiohttp.ClientError:  # Client error, bail.
        pass


async def gravatar_exists_in_db(session, gid):
    res = await session.database.search(
        index=session.database.dbs.mbox,
        size=1,
        body={"query": {"bool": {"must": [{"term": {"gravatar": gid}}]}}},
    )
    if res and len(res["hits"]["hits"]) == 1:
        return True
    return False


async def process(server: plugins.server.BaseServer, session: dict, indata: dict) -> aiohttp.web.Response:
    gid = indata.get("md5", "null")
    # Ensure md5 hash is valid
    if len(gid) != 32 or not all(b in "abcdef0123456789" for b in gid):
        gid = "null"
    # Valid and in cache??
    in_cache = gid in gravatars
    should_fetch = False
    # If valid but not cached, check if gravatar exists in the pony mail db
    if gid != "null" and not in_cache:
        should_fetch = await gravatar_exists_in_db(session, gid)
    # If valid and not in cache, fetch from gravatar.com
    if not in_cache and should_fetch:
        await fetch_gravatar(gid)
        # If we've hit the cache limit, pop the oldest element.
        if len(gravatars) > CACHE_LIMIT:
            to_pop = gravatars.pop(0)
            del gravatar_cache[to_pop]
    # if in cache, serve it.
    if gid in gravatars:
        img = gravatar_cache[gid]
        headers = {
          "Cache-Control": "max-age=86400",  # Expire gravatar in one day
        }
        return aiohttp.web.Response(headers=headers, content_type="image/png", body=img)
    return aiohttp.web.Response(content_type="text/plain", body="Could not fetch gravatar")


def register(server: plugins.server.BaseServer):
    return plugins.server.Endpoint(process)
