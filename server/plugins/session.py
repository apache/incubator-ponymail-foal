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
import plugins.token
import copy

FOAL_MAX_SESSION_AGE = 86400 * 7  # Max 1 week between visits before voiding a session
FOAL_SAVE_SESSION_INTERVAL = 3600  # Update sessions on disk max once per hour
DATABASE_NOT_CONNECTED = "Database not connected!"
OAUTH_PROVIDER_DEFAULT = "generic"

class SessionCredentials:
    uid: str
    name: str
    email: str
    provider: str
    authoritative: bool
    admin: bool
    oauth_data: dict

    def __init__(self, doc):
        if doc:
            self.uid = doc.get("uid", "")
            self.name = doc.get("name", "")
            self.email = doc.get("email", "")
            self.oauth_provider = doc.get("oauth_provider", OAUTH_PROVIDER_DEFAULT)
            self.authoritative = doc.get("authoritative", False)
            self.admin = doc.get("admin", False)
            self.oauth_data = doc.get("oauth_data", {})
        else:
            self.uid = ""
            self.name = ""
            self.email = ""
            self.oauth_provider = OAUTH_PROVIDER_DEFAULT
            self.authoritative = False
            self.admin = False
            self.oauth_data = {}


class SessionObject:
    cid: typing.Optional[str]
    cookie: str
    created: int
    last_accessed: int
    credentials: typing.Optional[SessionCredentials]
    database: typing.Optional[plugins.database.Database]
    remote: str
    host: str
    server: plugins.server.BaseServer
    token: bool  # True if this session was authenticated via a long-term API token
    token_scopes: typing.List[str]  # scopes granted to the API token (token auth only)
    token_invalid: bool  # True if a bearer token was presented but is invalid/expired

    def __init__(self, server: plugins.server.BaseServer, **kwargs):
        self.database = None
        self.server = server
        self.created = int(time.time())
        self.host = "??"
        self.remote = "??"
        self.token = False
        self.token_scopes = []
        self.token_invalid = False
        if kwargs:
            self.last_accessed = kwargs.get("last_accessed", 0)
            self.credentials = SessionCredentials(kwargs.get("credentials"))
            self.cookie = kwargs.get("cookie", "___")
            self.cid = kwargs.get("cid")
        else:
            self.last_accessed = self.created
            self.credentials = None
            self.cookie = str(uuid.uuid4())
            self.cid = None


async def get_session(
    server: plugins.server.BaseServer, request: aiohttp.web.BaseRequest
) -> SessionObject:
    session_id = None
    session = None
    now = int(time.time())

    # Long-term API token auth (Authorization: Bearer <token>).
    # Tokens bypass the cookie flow entirely and are not cached in memory;
    # each request is validated against the database.
    if server.config.tokens.enabled:
        bearer = plugins.token.token_from_request(request)
        if bearer:
            return await get_token_session(server, request, bearer, now)

    if request.headers.get("cookie"):
        for cookie_header in request.headers.getall("cookie"):
            cookies: http.cookies.SimpleCookie = http.cookies.SimpleCookie(
                cookie_header
            )
            if "ponymail" in cookies:
                session_id = cookies["ponymail"].value
                if not all(c in "abcdefg1234567890-" for c in session_id):
                    session_id = None
                break

    # Do we have the session in local memory?
    if session_id and session_id in server.data.sessions:
        x_session = server.data.sessions[session_id]
        if (now - x_session.last_accessed) > FOAL_MAX_SESSION_AGE:
            del server.data.sessions[session_id]
        else:

            # Make a copy so we don't have a race condition with the database pool object
            # In case the session is used twice within the same loop
            session = copy.copy(x_session)
            session.database = await server.dbpool.get()
            session.host = request.headers.get("X-Forwarded-Host", request.host)
            session.remote = request.remote

            # Do we need to update the timestamp in ES?
            if (now - session.last_accessed) > FOAL_SAVE_SESSION_INTERVAL:
                session.last_accessed = now
                await save_session(session)

            return session

    # If not in local memory, start a new session object
    session = SessionObject(server)
    session.database = await server.dbpool.get()
    session.host = request.headers.get("X-Forwarded-Host", request.host or "??")
    session.remote = request.remote or "??"

    # If a cookie was supplied, look for a session object in ES
    if session_id and session.database:
        try:
            session_doc = await session.database.get(
                session.database.dbs.db_session, id=session_id
            )
            last_update = session_doc["_source"]["updated"]
            session.cookie = session_id
            # Check that this cookie ain't too old. If it is, delete it and return bare-bones session object
            if (now - last_update) > FOAL_MAX_SESSION_AGE:
                await session.database.delete(
                    index=session.database.dbs.db_session, id=session_id
                )
                return session

            # Get CID and fecth the account data
            cid = session_doc["_source"]["cid"]
            if cid:
                account_doc = await session.database.get(
                    session.database.dbs.db_account, id=cid
                )
                creds = account_doc["_source"]["credentials"]
                internal = account_doc["_source"]["internal"]

                # Set session data
                session.cid = cid
                session.last_accessed = last_update
                creds["authoritative"] = (
                    internal.get("oauth_provider")
                    in server.config.oauth.authoritative_domains
                )
                creds["oauth_provider"] = internal.get("oauth_provider", OAUTH_PROVIDER_DEFAULT)
                creds["oauth_data"] = internal.get("oauth_data", {})
                # We update admin boolean whenever we fetch session doc, as they may have changed in yaml but not in ES.
                creds["admin"] = creds["authoritative"] and creds.get('email') in server.config.oauth.admins
                session.credentials = SessionCredentials(creds)

                # Save in memory storage
                server.data.sessions[session_id] = session

        except plugins.database.DBError:
            pass
    return session


def _apply_token_credentials(
    session: SessionObject, cid: typing.Optional[str], creds: dict, scopes: typing.List[str], now: int
) -> None:
    """Populate a session object from resolved token credentials."""
    session.cid = cid
    session.last_accessed = now
    session.token = True
    session.token_scopes = scopes
    session.credentials = SessionCredentials(creds)


def _cache_put(cache: dict, cache_max: int, key: str, entry: dict) -> None:
    """Insert an entry into the bounded token auth cache.

    When the cache is full we evict the oldest entries one at a time rather than
    flushing the whole cache (which would trigger a burst of database lookups).
    Every entry shares the same TTL, so the oldest inserted entry is also the
    one nearest to expiry. Re-inserting an existing key moves it to the newest
    position so insertion order keeps tracking age.
    """
    cache.pop(key, None)
    while cache and len(cache) >= cache_max:
        cache.pop(next(iter(cache)))
    cache[key] = entry


async def get_token_session(
    server: plugins.server.BaseServer,
    request: aiohttp.web.BaseRequest,
    bearer: str,
    now: int,
) -> SessionObject:
    """Build a session from a long-term API token.

    If the token is unknown or expired, the returned session has
    ``token_invalid`` set so the request layer can reject it with a clear error
    rather than silently downgrading to anonymous access.
    """
    session = SessionObject(server)
    session.database = await server.dbpool.get()
    session.host = request.headers.get("X-Forwarded-Host", request.host or "??")
    session.remote = request.remote or "??"

    tid = plugins.token.hash_token(bearer)
    cache_ttl = server.config.tokens.cache_ttl

    # Optional short-lived cache: skip the two database reads when this token was
    # validated within cache_ttl seconds. Disabled by default (cache_ttl == 0),
    # since caching delays the effect of revocation/expiry by up to cache_ttl.
    if cache_ttl > 0:
        cached = server.data.token_cache.get(tid)
        if cached:
            if cached["expiry"] > now:
                _apply_token_credentials(session, cached["cid"], cached["creds"], cached["scopes"], now)
                return session
            # Always drop an expired entry when we touch it, so stale credentials
            # never linger in the cache; fall through to a fresh lookup.
            server.data.token_cache.pop(tid, None)

    token_doc = await plugins.token.lookup_token(session.database, bearer)
    if not token_doc:
        session.token_invalid = True
        server.data.token_cache.pop(tid, None)  # drop any now-stale cache entry
        return session

    cid = token_doc.get("cid")
    try:
        account_doc = await session.database.get(session.database.dbs.db_account, id=cid)
    except plugins.database.DBError:
        session.token_invalid = True
        return session

    creds = account_doc["_source"]["credentials"]
    internal = account_doc["_source"]["internal"]
    # Distinguish a missing "scopes" field (legacy token from before scoping ->
    # full access, so it keeps working) from an explicit empty list (-> no
    # access). Using `or` here would fail open and treat [] as full access.
    stored_scopes = token_doc.get("scopes")
    scopes = list(plugins.token.ALL_SCOPES) if stored_scopes is None else stored_scopes
    creds["authoritative"] = internal.get("oauth_provider") in server.config.oauth.authoritative_domains
    creds["oauth_provider"] = internal.get("oauth_provider", OAUTH_PROVIDER_DEFAULT)
    creds["oauth_data"] = internal.get("oauth_data", {})
    creds["admin"] = creds["authoritative"] and creds.get("email") in server.config.oauth.admins
    _apply_token_credentials(session, cid, creds, scopes, now)

    # Populate the optional cache (bounded to avoid unbounded memory growth).
    if cache_ttl > 0:
        _cache_put(
            server.data.token_cache,
            server.config.tokens.cache_max,
            tid,
            {"expiry": now + cache_ttl, "cid": cid, "creds": creds, "scopes": scopes},
        )

    # Record usage, but no more than once per TOKEN_UPDATE_INTERVAL to avoid a
    # database write on every single API call.
    if (now - token_doc.get("last_used", 0)) > plugins.token.TOKEN_UPDATE_INTERVAL:
        try:
            await plugins.token.touch_token(session.database, token_doc["id"], now)
        except plugins.database.DBError:
            pass

    return session


async def set_session(server: plugins.server.BaseServer, cid: str, **credentials):
    """Create a new user session in the database"""
    session_id = str(uuid.uuid4())
    cookie: http.cookies.SimpleCookie = http.cookies.SimpleCookie()
    cookie["ponymail"] = session_id
    session = SessionObject(
        server, last_accessed=int(time.time()), cookie=session_id, cid=cid
    )
    session.credentials = SessionCredentials(credentials)
    server.data.sessions[session_id] = session

    # Grab temporary DB handle since session objects at init do not have this
    # We just need this to be able to save the session in ES.
    session.database = await server.dbpool.get()

    # Save session and account data
    await save_session(session)
    await save_credentials(session)

    # Put DB handle back into the pool
    server.dbpool.put_nowait(session.database)
    return cookie["ponymail"].OutputString()


async def save_session(session: SessionObject):
    """Save a session object in the ES database"""
    assert session.database, DATABASE_NOT_CONNECTED
    await session.database.index(
        index=session.database.dbs.db_session,
        id=session.cookie,
        body={
            "cookie": session.cookie,
            "cid": session.cid,
            "updated": session.last_accessed,
        },
    )


async def remove_session(session: SessionObject):
    """Remove a session object in the ES database"""
    assert session.database, DATABASE_NOT_CONNECTED
    await session.database.delete(index=session.database.dbs.db_session, id=session.cookie)


async def save_credentials(session: SessionObject):
    """Save a user account object in the ES database"""
    assert session.database, DATABASE_NOT_CONNECTED
    assert session.credentials, "Session object without credentials, cannot save!"
    await session.database.index(
        index=session.database.dbs.db_account,
        id=session.cid,
        body={
            "cid": session.cid,
            "credentials": {
                "email": session.credentials.email,
                "name": session.credentials.name,
                "uid": session.credentials.uid,
            },
            "internal": {
                "oauth_provider": session.credentials.oauth_provider,
                "oauth_data": session.credentials.oauth_data,
                "admin": session.credentials.admin,
            },
        },
    )
