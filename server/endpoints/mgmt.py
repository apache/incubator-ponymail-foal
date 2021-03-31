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
import plugins.auditlog
import typing
import aiohttp.web


async def process(
    server: plugins.server.BaseServer, session: plugins.session.SessionObject, indata: dict,
) -> typing.Union[dict, aiohttp.web.Response]:
    action = indata.get("action")
    docs = indata.get("documents", [])
    doc = indata.get("document")
    if not docs and doc:
        docs = [doc]
    if not session.credentials or not session.credentials.admin or not server.config.ui.mgmt_enabled:
        return aiohttp.web.Response(headers={}, status=403, text="You need administrative access to use this feature.")
    assert session.database, "No session database connection could be found!"

    # Viewing audit log?
    if action == "log":
        numentries = int(indata.get("size", 50))
        page = int(indata.get("page", 0))
        out = []
        async for entry in plugins.auditlog.view(session, page=page, num_entries=numentries, raw=True):
            out.append(entry)
        return {
            "entries": out
        }

    # Deleting/hiding a document?
    elif action == "delete":
        delcount = 0
        for doc in docs:
            assert isinstance(doc, str), "Document ID must be a string"
            email = await plugins.mbox.get_email(session, permalink=doc)
            if email and isinstance(email, dict) and plugins.aaa.can_access_email(session, email):
                email["deleted"] = True
                await session.database.index(
                    index=session.database.dbs.mbox, body=email, id=email["id"],
                )
                lid = email.get("list_raw", "??")
                await plugins.auditlog.add_entry(session, action="delete", target=doc, lid=lid, log=f"Removed email {doc} from {lid} archives")
                delcount += 1
        return aiohttp.web.Response(headers={}, status=200, text=f"Removed {delcount} emails from archives.")
    # Editing an email in place
    elif action == "edit":
        new_from = indata.get("from")
        new_subject = indata.get("subject")
        new_list = indata.get("list", "")
        private = True if indata.get("private", "no") == "yes" else False
        new_body = indata.get("body", "")

        # Check for consistency so we don't pollute the database
        assert isinstance(doc, str) and doc, "Document ID is missing or invalid"
        assert isinstance(new_from, str), "Author field must be a text string!"
        assert isinstance(new_subject, str), "Subject field must be a text string!"
        assert isinstance(new_list, str), "List ID field must be a text string!"
        assert isinstance(new_body, str), "Email body must be a text string!"

        # Convert List-ID after verification
        lid = "<" + new_list.strip("<>").replace("@", ".") + ">"  # foo@bar.baz -> <foo.bar.baz>

        email = await plugins.mbox.get_email(session, permalink=doc)
        if email and isinstance(email, dict) and plugins.aaa.can_access_email(session, email):
            email["from_raw"] = new_from
            email["from"] = new_from
            email["subject"] = new_subject
            email["private"] = private
            origin_lid = email["list_raw"]
            email["list"] = lid
            email["list_raw"] = lid
            email["body"] = new_body

            # Save edited email
            await session.database.index(
                index=session.database.dbs.mbox, body=email, id=email["id"],
            )

            # Fetch source, mark as deleted (modified) and save
            # We do this, as we can't edit the source easily, so we mark it as off-limits instead.
            source = await plugins.mbox.get_source(session, permalink=email["id"], raw=True)
            if source:
                source = source["_source"]
                source["deleted"] = True
                await session.database.index(
                    index=session.database.dbs.source, body=source, id=email["id"],
                )

            await plugins.auditlog.add_entry(session, action="edit", target=doc, lid=lid,
                                             log= f"Edited email {doc} from {origin_lid} archives ({origin_lid} -> {lid})")

            return aiohttp.web.Response(headers={}, status=200, text=f"Email successfully saved")
        return aiohttp.web.Response(headers={}, status=404, text=f"Email not found!")

    return aiohttp.web.Response(headers={}, status=404, text=f"Unknown mgmt command requested")


def register(server: plugins.server.BaseServer):
    return plugins.server.Endpoint(process)
