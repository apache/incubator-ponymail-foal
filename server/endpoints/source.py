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

"""Simple endpoint that returns an email source"""

import plugins.server
import plugins.session
import plugins.messages
import aiohttp.web
import plugins.aaa


async def process(
    server: plugins.server.BaseServer, session: plugins.session.SessionObject, indata: dict,
) -> aiohttp.web.Response:
    listid = indata.get("list", "")
    # First, assume permalink and look up the email based on that
    email = await plugins.messages.get_email(session, permalink=indata.get("id"))

    # If not found via permalink, it might be message-id instead, so try that
    if email is None:
        email = await plugins.messages.get_email(session, messageid=indata.get("id"), listid=listid)

    if email and isinstance(email, dict) and not email.get("deleted"):
        if plugins.aaa.can_access_email(session, email):
            source = await plugins.messages.get_source(session, permalink=email["dbid"])
            if source and not source["_source"].get("deleted"):
                return aiohttp.web.Response(
                    headers={"Content-Type": "text/plain"}, status=200, text=source["_source"]["source"],
                )
    return aiohttp.web.Response(headers={}, status=404, text="Email not found")


def register(server: plugins.server.BaseServer):
    return plugins.server.Endpoint(process)
