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

"""Endpoint for returning emails in mbox format as a single archive"""
import asyncio
import plugins.server
import plugins.session
import plugins.messages
import plugins.defuzzer
import re
import typing
import aiohttp.web
import asyncio.exceptions


async def convert_source(session: plugins.session.SessionObject, email: dict):
    source = await plugins.messages.get_source(session, permalink=email.get("dbid", email["mid"]))
    if source:
        source_as_text = source["_source"]["source"]
        # Convert to mboxrd format
        mboxrd_source = ""
        line_no = 0
        for line in source_as_text.split("\n"):
            line_no += 1
            if line_no > 1 and re.match(r"^>*From\s+", line):
                line = ">" + line
            mboxrd_source += line + "\n"
        return mboxrd_source
    return ""


async def process(
    server: plugins.server.BaseServer,
    request: aiohttp.web.BaseRequest,
    session: plugins.session.SessionObject,
    indata: dict,
) -> typing.Union[dict, aiohttp.web.Response, aiohttp.web.StreamResponse]:

    lid = indata.get("list", "_")
    domain = indata.get("domain", "_")

    try:
        query_defuzzed = plugins.defuzzer.defuzz(indata, list_override="@" in lid and lid or None)
    except AssertionError as e:  # If defuzzer encounters syntax errors, it will throw an AssertionError
        return aiohttp.web.Response(
            headers={
                "content-type": "text/plain",
            },
            status=500,
            text=str(e),
        )
    results = await plugins.messages.query(
        session,
        query_defuzzed,
        query_limit=server.config.database.max_hits,
        epoch_order="asc"
    )

    # Figure out a sane filename
    xlist = re.sub(r"[^-_.a-z0-9]+", "_", lid)
    xdomain = re.sub(r"[^-_.a-z0-9]+", "_", domain)
    dlfile = f"{xlist}-{xdomain}.mbox"
    headers = {"Content-Type": "application/mbox", "Content-Disposition": f"attachment; filename={dlfile}"}

    # Return mbox archive with filename as a stream
    response = aiohttp.web.StreamResponse(status=200, headers=headers)
    response.enable_chunked_encoding()
    await response.prepare(request)
    for email in results:
        mboxrd_source = await convert_source(session, email)
        try:
            async with server.streamlock:
                await asyncio.wait_for(response.write(mboxrd_source.encode("utf-8")), timeout=5)
        except (TimeoutError, RuntimeError, asyncio.exceptions.CancelledError):
            break  # Writing stream failed, break it off.
    return response


def register(server: plugins.server.BaseServer):
    # Note that this is a StreamingEndpoint!
    return plugins.server.StreamingEndpoint(process)
