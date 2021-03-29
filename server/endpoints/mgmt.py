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

"""Management endpoint for GDPR operations"""

import plugins.server
import plugins.session
import plugins.mbox
import plugins.defuzzer
import typing
import aiohttp.web
import time


async def process(
    server: plugins.server.BaseServer, session: plugins.session.SessionObject, indata: dict,
) -> typing.Optional[dict]:
    action = indata.get("action")
    docs = indata.get("documents", [])
    doc = indata.get("document")
    if not docs and doc:
        docs = [doc]
    if not session.credentials.admin or not server.config.ui.mgmt_enabled:
        return aiohttp.web.Response(headers={}, status=403, text="You need administrative access to use this feature.")

    # Deleting/hiding a document?
    if action == "delete":
        delcount = 0
        for doc in docs:
            email = await plugins.mbox.get_email(session, permalink=doc)
            if email and isinstance(email, dict) and plugins.aaa.can_access_email(session, email):
                email["deleted"] = True
                await session.database.index(
                    index=session.database.dbs.mbox, body=email, id=email["id"],
                )
                lid = email.get("list_raw")
                await session.database.index(
                    index=session.database.dbs.auditlog,
                    body={
                        "date": time.strftime("%Y/%m/%d %H:%M:%S", time.gmtime(time.time())),
                        "action": "delete",
                        "remote": session.remote,
                        "author": f"{session.credentials.uid}@{session.credentials.oauth_provider}",
                        "target": doc,
                        "lid": lid,
                        "log": f"Removed email {doc} from {lid} archives",
                    },
                )
                delcount += 1
        return aiohttp.web.Response(headers={}, status=200, text=f"Removed {delcount} emails from archives.")


def register(server: plugins.server.BaseServer):
    return plugins.server.Endpoint(process)
