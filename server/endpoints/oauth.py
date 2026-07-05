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

"""Parent OAuth endpoint for Pony Mail codename Foal"""

import plugins.server
import plugins.session
import plugins.oauthGeneric
import plugins.oauthGoogle
import plugins.oauthGithub
import plugins.database
import plugins.token
import typing
import aiohttp.web
import hashlib

def debug(server, text):
    if server.api_logger:
        server.api_logger.debug(text)

async def process(
    server: plugins.server.BaseServer, session: plugins.session.SessionObject, indata: dict,
) -> typing.Union[dict, aiohttp.web.Response]:

    debug(server, f"oauth/indata: {indata}")
    key = indata.get("key", "")
    state = indata.get("state")
    code = indata.get("code")
    id_token = indata.get("id_token")

    rv: typing.Optional[dict] = None

    # Google OAuth - currently fetches email address only
    if key == "google" and id_token and server.config.oauth.google_client_id:
        rv = await plugins.oauthGoogle.process(indata, session, server)

    # GitHub OAuth - Fetches name and email
    elif key == "github" and code and server.config.oauth.github_client_id:
        rv = await plugins.oauthGithub.process(indata, session, server)

    # Generic OAuth handler, only one we support for now. Works with ASF OAuth.
    elif state and code:
        rv = await plugins.oauthGeneric.process(indata, session, server)

    if rv:
        debug(server, f"oauth/rv: {rv}")
        # Get UID, fall back to using email address
        uid = rv.get("uid")
        if not uid:
            uid = rv.get("email")
        if uid:
            oauth_provider = rv.get("oauth_domain", plugins.session.OAUTH_PROVIDER_DEFAULT)
            cid = hashlib.shake_128(
                ("%s-%s" % (oauth_provider, uid)).encode("ascii", "ignore")
            ).hexdigest(16)
            authoritative = oauth_provider in server.config.oauth.authoritative_domains
            admin = authoritative and rv.get("email") in server.config.oauth.admins
            debug(server, f"oauth/aa: {authoritative} {admin}")

            # Capture the identity we had on file *before* set_session overwrites
            # the account document, so we can tell whether this login represents a
            # changed upstream setup (see the token purge below).
            prior_oauth_data: typing.Optional[dict] = None
            had_prior_account = False
            if (
                server.config.tokens.enabled
                and server.config.tokens.revoke_on_identity_change
                and session.database
            ):
                try:
                    prior_doc = await session.database.get(
                        session.database.dbs.db_account, id=cid
                    )
                    had_prior_account = True
                    prior_oauth_data = prior_doc["_source"].get("internal", {}).get("oauth_data", {})
                except plugins.database.DBError:
                    pass

            cookie = await plugins.session.set_session(
                server,
                cid,
                uid=uid,
                name=rv.get("name") or rv.get("fullname"),
                email=rv.get("email"),
                # Authoritative if OAuth domain is in the authoritative oauth section in ponymail.yaml
                # Required for access to private emails
                authoritative=authoritative,
                oauth_provider=oauth_provider,
                oauth_data=rv,
                admin=admin,
            )

            # If the user's upstream identity/permissions changed since we last
            # saw them, drop every long-term token they hold: a token minted
            # under the old setup must not survive a credential reset or a change
            # in group membership. Only acts on an existing account (a first-ever
            # login has nothing to revoke) and is best-effort — a purge failure
            # must never block the login itself.
            if (
                had_prior_account
                and session.database
                and plugins.token.oauth_setup_changed(prior_oauth_data, rv)
            ):
                try:
                    purged = await plugins.token.purge_tokens_for_cid(session.database, cid)
                    if purged:
                        debug(server, f"oauth: purged {purged} token(s) for {cid} after identity change")
                except plugins.database.DBError:
                    pass

            # This could be improved upon, instead of a raw response return value
            return aiohttp.web.Response(
                headers={"set-cookie": cookie, "content-type": "application/json"}, status=200, text='{"okay": true}',
            )

    return {"okay": False, "message": "Could not process OAuth login!"}


def register(_server: plugins.server.BaseServer):
    return plugins.server.Endpoint(process)
