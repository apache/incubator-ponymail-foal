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
Long-term API token management endpoint for Pony Mail codename Foal.

Actions (via ?action= or JSON body):
  * list   (default) - list the calling user's tokens (metadata only)
  * create           - mint a new token; the raw secret is returned ONCE
  * revoke           - delete a token by id

Tokens themselves are used by sending 'Authorization: Bearer <token>' on any
API request; see plugins/token.py and plugins/session.py.
"""

import time
import typing

import aiohttp.web

import plugins.auditlog
import plugins.database
import plugins.server
import plugins.session
import plugins.token


def _json(payload: dict, status: int = 200) -> aiohttp.web.Response:
    import json

    return aiohttp.web.Response(
        headers={"content-type": "application/json"},
        status=status,
        text=json.dumps(payload),
    )


async def process(
    server: plugins.server.BaseServer,
    request: aiohttp.web.BaseRequest,
    session: plugins.session.SessionObject,
    indata: dict,
) -> typing.Union[dict, aiohttp.web.Response]:

    if not server.config.tokens.enabled:
        return _json({"okay": False, "message": "API tokens are disabled on this server."}, 403)

    # Must be logged in (interactively) to manage tokens.
    if not session.credentials or not session.cid:
        return _json({"okay": False, "message": "You must be logged in to manage API tokens."}, 403)

    # Tokens may not be managed using token authentication - this prevents a
    # leaked token from silently minting more tokens or covering its tracks.
    if session.token:
        return _json(
            {"okay": False, "message": "API tokens must be managed via an interactive login, not a token."},
            403,
        )

    assert session.database, "Session not connected to database!"
    action = indata.get("action", "list")

    if action in ("create", "revoke"):
        if request.method != "POST" or request.content_type != "application/json" or "action" in request.query:
            return _json(
                {"okay": False, "message": "Token create/revoke actions require a JSON POST body."},
                405,
            )

    if action == "list":
        tokens = await plugins.token.list_tokens(session.database, session.cid)
        return {"okay": True, "tokens": tokens}

    if action == "create":
        existing = await plugins.token.count_tokens(session.database, session.cid)
        if existing >= server.config.tokens.max_tokens:
            return _json(
                {
                    "okay": False,
                    "message": "You already have the maximum of %d tokens. Revoke one first."
                    % server.config.tokens.max_tokens,
                },
                400,
            )

        description = str(indata.get("description", "")).strip() or "API token"

        # Determine lifetime (seconds). Fall back to the server default, and
        # clamp to the configured maximum if one is set.
        default_age = server.config.tokens.default_age
        max_age = server.config.tokens.max_age
        requested = indata.get("lifetime")
        if requested is None or requested == "":
            age = default_age
        else:
            try:
                age = int(str(requested))
            except (ValueError, TypeError):
                age = default_age
        if age < 0:
            age = default_age
        if max_age > 0 and (age == 0 or age > max_age):
            age = max_age
        expires = int(time.time()) + age if age > 0 else 0

        # Scopes restrict what the token may do (defaults to read-only).
        scopes = plugins.token.normalize_scopes(indata.get("scopes"))

        result = await plugins.token.create_token(session.database, session.cid, description, expires, scopes)
        # Best-effort audit trail; never block returning the one-time secret.
        try:
            await plugins.auditlog.add_entry(
                session,
                "token_create",
                result["id"],
                "",
                "Created API token '%s' (scopes: %s)" % (description, ", ".join(scopes)),
                refresh=False,
            )
        except plugins.database.DBError:
            pass
        return {"okay": True, **result}

    if action == "revoke":
        tid = indata.get("id")
        if not tid:
            return _json({"okay": False, "message": "No token id supplied."}, 400)
        ok = await plugins.token.revoke_token(session.database, session.cid, str(tid))
        if ok:
            try:
                await plugins.auditlog.add_entry(
                    session, "token_revoke", str(tid), "", "Revoked API token %s" % tid, refresh=False
                )
            except plugins.database.DBError:
                pass
            return {"okay": True, "message": "Token revoked."}
        return _json({"okay": False, "message": "Token not found."}, 404)

    return _json({"okay": False, "message": "Unknown action '%s'." % action}, 400)


def register(_server: plugins.server.BaseServer):
    return plugins.server.StreamingEndpoint(process)
