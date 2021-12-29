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

import plugins.server
import plugins.session
import plugins.messages
import typing


async def process(
    server: plugins.server.BaseServer, session: plugins.session.SessionObject, indata: dict,
) -> typing.Optional[dict]:
    mailid = indata.get("id", "")
    listid = indata.get("list", "")
    email = await plugins.messages.get_email(session, permalink=mailid)
    if not email:
        email = await plugins.messages.get_email(session, messageid=mailid, listid=listid)
    # The id is passed via the path thread/id
    # This means that + is converted into space
    # So we need to try both space and '+', and hope no msg ids contain both
    if not email and ' ' in mailid: # only try again if we need to
        mailid = mailid.replace(" ", "+")
        email = await plugins.messages.get_email(session, messageid=mailid, listid=listid)
    if not email:
        return None
    if indata.get("find_parent"):
        parent = await plugins.messages.find_parent(session, email)
        if parent:
            email = parent
    if email and isinstance(email, dict):
        thread, emails, _pdocs = await plugins.messages.fetch_children(session, email, short=True)
    else:
        return None

    email["children"] = thread
    emails.append(email)
    for email in emails:
        plugins.messages.trim_email(email, external=True)
    return {
        "thread": email,
        "emails": emails,
    }


def register(server: plugins.server.BaseServer):
    return plugins.server.Endpoint(process)
