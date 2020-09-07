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

"""This is the user session handler for PyPony"""

import http.cookies
import time
import typing
import uuid

import aiohttp.web

import plugins.database
import plugins.server
import copy

PYPONY_MAX_SESSION_AGE = 86400 * 7  # Max 1 week between visits before voiding a session


class SessionCredentials:
    uid: str
    name: str
    email: str
    provider: str
    authoritative: bool
    admin: bool
    oauth_data: dict

    def __init__(self, doc: typing.Dict = None):
        if doc:
            self.uid = doc.get('uid', '')
            self.name = doc.get('name', '')
            self.email = doc.get('email', '')
            self.provider = doc.get('provider', 'generic')
            self.authoritative = doc.get('authoritative', False)
            self.admin = doc.get('admin', False)
            self.oauth_data = doc.get('oauth_data', {})
        else:
            self.uid = ""
            self.name = ""
            self.email = ""
            self.provider = "generic"
            self.authoritative = False
            self.admin = False
            self.oauth_data = {}


class SessionObject:
    uid: str
    created: int
    last_accessed: int
    credentials: SessionCredentials
    database: typing.Optional[plugins.database.Database]

    def __init__(self, server: plugins.server.BaseServer, doc=None):
        self.database = None
        if not doc:
            now = int(time.time())
            self.created = now
            self.last_accessed = now
            self.credentials = SessionCredentials()
            self.uid = str(uuid.uuid4())
        else:
            self.created = doc["created"]
            self.last_accessed = doc["last_accessed"]
            self.credentials = SessionCredentials(doc["credentials"])
            self.uid = doc["uid"]


async def get_session(
    server: plugins.server.BaseServer, request: aiohttp.web.BaseRequest
    ) -> SessionObject:
    session_id = None
    session = None
    if request.headers.get("cookie"):
        for cookie_header in request.headers.getall("cookie"):
            cookies: http.cookies.SimpleCookie = http.cookies.SimpleCookie(
                cookie_header
            )
            if "ponymail" in cookies:
                session_id = cookies["ponymail"].value
                break

    if session_id in server.data.sessions:
        x_session = server.data.sessions[session_id]
        now = int(time.time())
        if (now - x_session.last_accessed) > PYPONY_MAX_SESSION_AGE:
            del server.data.sessions[session_id]
        else:
            # Make a copy so we don't have a race condition with the database pool object
            # In case the session is used twice within the same loop
            session = copy.copy(x_session)
    if not session:
        session = SessionObject(server)
    session.database = await server.dbpool.get()
    return session


async def set_session(server: plugins.server.BaseServer, **credentials):
    """Create a new user session in the database"""
    session_id = str(uuid.uuid4())
    cookie: http.cookies.SimpleCookie = http.cookies.SimpleCookie()
    cookie["ponymail"] = session_id
    session = SessionObject(server)
    session.credentials = SessionCredentials(credentials)
    server.data.sessions[session_id] = session
    return cookie.output(header='').lstrip()

