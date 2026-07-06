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

"""Forward-compatibility shim for asfquart / ATR token semantics.

This module is **not** wired into the request path. It exists to demonstrate,
in code, how PonyMail's API-token session maps onto the session/scope shape used
by `asfquart <https://github.com/apache/infrastructure-asfquart>`_ and the token
subsystem built on top of it in `ATR (apache/tooling-trusted-releases)`. Keeping
the mapping here (and tested) means that if PonyMail ever adopts asfquart's
``app.token_handler`` seam, or migrates onto Quart wholesale, the translation is
a single reviewed function rather than a scattered rewrite. See
``docs/asfquart_migration.md`` for the rationale and the step-by-step plan.

Nothing in here imports asfquart -- it is not a dependency. We only produce
dicts shaped the way ``asfquart.session.ClientSession`` expects and predicates
shaped the way ``asfquart.auth.Requirements`` expects.
"""

import typing

import plugins.token

# asfquart stores per-session scope under ``session.metadata["scope"]`` (see its
# personal_access_tokens.py example, which ATR follows). Mirror that key exactly
# so a future asfquart token_handler can read our scopes without translation.
SCOPE_METADATA_KEY = "scope"


def to_asfquart_session(session: typing.Any) -> dict:
    """Render a PonyMail ``SessionObject`` as an asfquart session dict.

    The returned dict matches the fields ``asfquart.session.ClientSession``
    reads (``uid``, ``email``, ``fullname``, ``roleaccount``, ``metadata`` ...).
    An asfquart ``token_handler`` callback could return this dict verbatim.

    Mapping notes -- PonyMail tracks a narrower identity than asfquart's
    LDAP/OAuth-backed session, so some asfquart fields have no PonyMail source:

      * ``roleaccount``: True for a token (Bearer) session. This matches
        asfquart's own PAT example, which models personal access tokens as role
        accounts; an interactive cookie session maps to a normal user (False).
      * ``isRoot``: mapped from PonyMail's ``admin`` flag, the closest analogue
        to asfquart's infra-root membership.
      * ``isMember`` / ``isChair`` / ``pmcs`` / ``projects`` / ``mfa``: PonyMail
        does not track ASF org roles, so these stay at their empty defaults.
        A Quart/asfquart deployment would populate them from the OAuth payload.
      * ``scope``: a token session carries the token's granted scopes; an
        interactive session is unrestricted, represented here as all scopes.
    """
    creds = getattr(session, "credentials", None)
    is_token = bool(getattr(session, "token", False))
    scopes = (
        list(getattr(session, "token_scopes", None) or [])
        if is_token
        else list(plugins.token.ALL_SCOPES)
    )
    return {
        "uid": getattr(creds, "uid", "") if creds else "",
        "email": getattr(creds, "email", "") if creds else "",
        "fullname": getattr(creds, "name", "") if creds else "",
        "isMember": False,
        "isChair": False,
        "isRoot": bool(getattr(creds, "admin", False)) if creds else False,
        "pmcs": [],
        "projects": [],
        "mfa": False,
        "roleaccount": is_token,
        "metadata": {
            SCOPE_METADATA_KEY: scopes,
            # Extra PonyMail context an asfquart consumer can ignore but that we
            # keep so no information is lost across the translation.
            "api_token": is_token,
            "oauth_provider": getattr(creds, "oauth_provider", "") if creds else "",
            "authoritative": bool(getattr(creds, "authoritative", False)) if creds else False,
        },
    }


def scope_requirement(scope: str) -> typing.Callable[[dict], typing.Tuple[bool, str]]:
    """Build an asfquart-style ``Requirements`` predicate for a token scope.

    asfquart gates endpoints with ``@asfquart.auth.require(Requirements.foo)``,
    where each requirement is ``fn(client_session) -> (passes, message)``. This
    returns such a predicate for one of our token scopes, so the very same
    per-endpoint rule enforced today by ``main.py`` via ``token.token_allows``
    could instead be attached as::

        @asfquart.auth.require(scope_requirement(token.required_scope(handler)))

    once PonyMail runs under asfquart. An interactive (non-token) session, which
    ``to_asfquart_session`` renders with all scopes, satisfies every scope -
    matching today's rule that only token sessions are scope-restricted.
    """

    message = "This API token lacks the '%s' scope required for this endpoint." % scope

    def _requirement(client_session: dict) -> typing.Tuple[bool, str]:
        metadata = (client_session or {}).get("metadata") or {}
        granted = metadata.get(SCOPE_METADATA_KEY) or []
        return scope in granted, message

    _requirement.__name__ = "scope_%s" % scope
    return _requirement
