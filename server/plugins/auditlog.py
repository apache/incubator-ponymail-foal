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

"""
This is the Audit log library for Pony Mail codename Foal
It manages viewing and editing the audit log.
"""

import plugins.session
import typing
import time


class AuditLogEntry:
    _keys: tuple = (
        "id",
        "date",
        "action",
        "remote",
        "author",
        "target",
        "lid",
        "log",
    )

    def __init__(self, doc):
        for key in self._keys:
            if key in doc:
                setattr(self, key, doc[key])


async def view(
    session: plugins.session.SessionObject, page: int = 0, num_entries: int = 50, raw: bool = False, filter: typing.Tuple = ()
) -> typing.AsyncGenerator:
    """ Returns N entries from the audit log, paginated """
    assert session.database, "No database connection could be found!"
    if not filter:
        res = await session.database.search(
            index=session.database.dbs.db_auditlog, size=num_entries, from_=page * num_entries, sort="date:desc",
        )
    else:
        res = await session.database.search(
            index=session.database.dbs.db_auditlog, size=num_entries, from_=page * num_entries, sort="date:desc",
            body={
                "query": {"bool": {"must": [{"terms": {"action": filter}}]}}
            },
        )

    for doc in res["hits"]["hits"]:
        doc["_source"]["id"] = doc["_id"]
        if raw:
            yield doc["_source"]
        else:
            yield AuditLogEntry(doc["_source"])


async def add_entry(session: plugins.session.SessionObject, action: str, target: str, lid: str, log: str) -> None:
    """ Adds an entry to the audit log"""

    # Default log entries based on type
    if not log and action == "delete":
        log = f"Removed email {target} from {lid} archives"
    if not log and action == "edit":
        log = f"Modified email {target} from {lid} archives"
    assert session.credentials, "No session credentials could be found!"
    assert session.database, "Session not connected to database!"
    await session.database.index(
        index=session.database.dbs.db_auditlog,
        body={
            "date": time.strftime("%Y/%m/%d %H:%M:%S", time.gmtime(time.time())),
            "action": action,
            "remote": session.remote,
            "author": f"{session.credentials.uid}@{session.credentials.oauth_provider}",
            "target": target,
            "lid": lid,
            "log": log,
        },
        refresh='wait_for',
    )
