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
import plugins.server
import plugins.session
import plugins.messages
import plugins.defuzzer
import re
import typing
import aiohttp.web


async def process(
    server: plugins.server.BaseServer, session: plugins.session.SessionObject, indata: dict,
) -> typing.Union[dict, aiohttp.web.Response]:

    lid = indata.get("list", "_")
    domain = indata.get("domain", "_")
    
    try:
        query_defuzzed = plugins.defuzzer.defuzz(indata, list_override="@" in lid and lid or None)
    except AssertionError as e:  # If defuzzer encounters syntax errors, it will throw an AssertionError
        return aiohttp.web.Response(headers={"content-type": "text/plain",}, status=500, text=str(e))
    results = await plugins.messages.query(session, query_defuzzed, query_limit=server.config.database.max_hits,)

    sources = []
    for email in results:
        source = await plugins.messages.get_source(session, permalink=email["mid"])
        if source:
            stext = source["_source"]["source"]
            # Convert to mboxrd format
            mboxrd_source = ""
            line_no = 0
            for line in stext.split("\n"):
                line_no += 1
                if line_no > 1 and re.match(r"^>*From\s+", line):
                    line = ">" + line
                mboxrd_source += line + "\n"
            sources.append(mboxrd_source)

    # Figure out a sane filename
    xlist = re.sub(r"[^-_.a-z0-9]+", "_", lid)
    xdomain = re.sub(r"[^-_.a-z0-9]+", "_", domain)
    dlfile = f"{xlist}-{xdomain}.mbox"

    # Return mbox archive with filename
    return aiohttp.web.Response(
        headers={"Content-Type": "application/mbox", "Content-Disposition": f"attachment; filename={dlfile}",},
        status=200,
        text="\n\n".join(sources),
    )


def register(server: plugins.server.BaseServer):
    return plugins.server.Endpoint(process)
