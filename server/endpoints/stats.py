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

"""Simple endpoint that returns the server's gathered activity data"""
""" THIS ONLY DEALS WITH PUBLIC EMAILS FOR NOW - AAA IS BEING WORKED ON"""
import plugins.server
import plugins.session
import plugins.mbox
import plugins.defuzzer
import plugins.offloader
import re
import collections
import email.utils
import typing

PYPONY_RE_PREFIX = re.compile(r"^([a-zA-Z]+:\s*)+")


async def process(
    server: plugins.server.BaseServer,
    session: plugins.session.SessionObject,
    indata: dict,
) -> dict:

    query_defuzzed = plugins.defuzzer.defuzz(indata)
    query_defuzzed_nodate = plugins.defuzzer.defuzz(indata, nodate=True)
    results = await plugins.mbox.query(
        session,
        query_defuzzed,
        query_limit=server.config.database.max_hits,
        shorten=True,
    )

    for msg in results:
        msg["gravatar"] = plugins.mbox.gravatar(msg)

    wordcloud = None
    if server.config.ui.wordcloud:
        wordcloud = await plugins.mbox.wordcloud(session, query_defuzzed)
    first_year, last_year = await plugins.mbox.get_years(session, query_defuzzed_nodate)

    threads = plugins.mbox.ThreadConstructor(results)
    tstruct, authors = await server.runners.run(threads.construct)
    xlist = indata.get("list", "*")
    xdomain = indata.get("domain", "*")

    all_authors = sorted(
        [[author, count] for author, count in authors.items()], key=lambda x: x[1]
    )
    top10_authors = []
    for x in [x for x in reversed([x for x in all_authors])][:10]:
        author, count = x
        name, address = email.utils.parseaddr(author)
        top10_authors.append(
            {
                "email": address,
                "name": name,
                "count": count,
                "gravatar": plugins.mbox.gravatar(author),
            }
        )

    # Trim email data so as to reduce download sizes
    for msg in results:
        plugins.mbox.trim_email(msg, external=True)

    return {
        "firstYear": first_year,
        "lastYear": last_year,
        "hits": len(results),
        "numparts": len(authors),
        "no_threads": len(tstruct),
        "emails": list(sorted(results, key=lambda x: x['epoch'])),
        "cloud": wordcloud,
        "participants": top10_authors,
        "thread_struct": tstruct,
        "search_list": f"<{xlist}.{xdomain}>",
        "domain": xdomain,
        "list": f"{xlist}@{xdomain}",
        "searchParams": indata,
    }


def register(server: plugins.server.BaseServer):
    return plugins.server.Endpoint(process)
