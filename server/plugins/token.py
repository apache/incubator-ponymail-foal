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
Long-term API token handling for Pony Mail codename Foal.

Tokens let a user authenticate to the API programmatically by sending an
``Authorization: Bearer <token>`` header, without going through the interactive
OAuth flow and without being subject to the short session-cookie lifetime.

Security notes:
  * The raw token is shown to the user exactly once, at creation time.
  * Only a SHA-256 digest of the token is stored server-side, so a database
    leak does not, by itself, expose usable credentials.
  * A token grants the same access as the account that created it (including
    any private lists that account can reach).
"""

import hashlib
import json
import secrets
import time
import typing

import aiohttp.web

import plugins.database

# A short, greppable prefix so tokens are recognisable in logs and headers.
TOKEN_PREFIX = "pmt_"  # "Pony Mail Token"
# 32 bytes == 256 bits of entropy (~43 url-safe characters).
TOKEN_NBYTES = 32
# Only rewrite a token's "last_used" timestamp at most this often (seconds).
TOKEN_UPDATE_INTERVAL = 3600

# Token scopes. A token's effective access is the intersection of its owner's
# account permissions and its scopes, so a scope can only *restrict* access -
# it never grants more than the underlying account already has.
SCOPE_READ = "read"  # search + fetch emails/threads/sources/mbox, read preferences
SCOPE_WRITE = "write"  # send email (compose)
SCOPE_ADMIN = "admin"  # administrative operations (hide/delete/edit)
ALL_SCOPES = (SCOPE_READ, SCOPE_WRITE, SCOPE_ADMIN)
DEFAULT_SCOPES = (SCOPE_READ,)  # least privilege when the caller does not choose

# Which scope each API endpoint requires. Endpoints not listed require read.
_WRITE_ENDPOINTS = frozenset({"compose"})
_ADMIN_ENDPOINTS = frozenset({"mgmt"})


def required_scope(handler: str) -> str:
    """Return the token scope required to reach the given API endpoint."""
    if handler in _ADMIN_ENDPOINTS:
        return SCOPE_ADMIN
    if handler in _WRITE_ENDPOINTS:
        return SCOPE_WRITE
    return SCOPE_READ


def normalize_scopes(raw: typing.Any) -> typing.List[str]:
    """Coerce caller-supplied scopes into a validated, de-duplicated list.

    Accepts a list/tuple or a space/comma-separated string. Unknown scopes are
    dropped; falls back to DEFAULT_SCOPES when nothing valid remains.
    """
    if isinstance(raw, str):
        items = raw.replace(",", " ").split()
    elif isinstance(raw, (list, tuple)):
        items = [str(x) for x in raw]
    else:
        items = []
    wanted = {i.strip().lower() for i in items}
    # Keep canonical order, drop unknowns/duplicates.
    scopes = [s for s in ALL_SCOPES if s in wanted]
    return scopes or list(DEFAULT_SCOPES)


def token_allows(session: typing.Any, handler: str) -> bool:
    """Whether a (possibly token-authenticated) session may reach an endpoint.

    Cookie (non-token) sessions are never restricted here. A token session must
    carry the scope the endpoint requires.
    """
    if not getattr(session, "token", False):
        return True
    return required_scope(handler) in (getattr(session, "token_scopes", None) or [])


def generate_token() -> str:
    """Return a fresh random token string (the secret shown to the user once)."""
    return TOKEN_PREFIX + secrets.token_urlsafe(TOKEN_NBYTES)


def hash_token(token: str) -> str:
    """Return the storage id for a token: its SHA-256 hex digest.

    We store only this digest, never the raw token.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_from_request(request: aiohttp.web.BaseRequest) -> typing.Optional[str]:
    """Extract a bearer token from the Authorization header, or None."""
    auth = request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        candidate = parts[1].strip()
        if candidate.startswith(TOKEN_PREFIX):
            return candidate
    return None


async def create_token(
    database: plugins.database.Database,
    cid: str,
    description: str,
    expires: int,
    scopes: typing.Sequence[str],
) -> dict:
    """Create and persist a new token for account ``cid``.

    ``expires`` is an absolute epoch timestamp, or 0 for a token that never
    expires. ``scopes`` restricts what the token may do. Returns the stored
    metadata plus the raw ``token`` secret, which is the only time the raw
    token is ever available.
    """
    raw = generate_token()
    tid = hash_token(raw)
    now = int(time.time())
    doc = {
        "id": tid,
        "cid": cid,
        "description": description[:256],
        "created": now,
        "expires": int(expires),
        "last_used": 0,
        "scopes": list(scopes),
    }
    await database.index(index=database.dbs.db_token, id=tid, body=doc, refresh="wait_for")
    result = dict(doc)
    result.pop("cid", None)  # internal linkage, not needed by the caller
    result["token"] = raw
    return result


async def list_tokens(database: plugins.database.Database, cid: str) -> typing.List[dict]:
    """Return metadata (never the raw secret) for all tokens owned by ``cid``."""
    res = await database.search(
        index=database.dbs.db_token,
        size=100,
        sort="created:desc",
        body={"query": {"term": {"cid": cid}}},
    )
    out = []
    for hit in res["hits"]["hits"]:
        src = hit["_source"]
        src.pop("cid", None)  # do not echo internal account linkage
        out.append(src)
    return out


async def revoke_token(database: plugins.database.Database, cid: str, tid: str) -> bool:
    """Delete token ``tid`` if it belongs to ``cid``. Returns True on success."""
    try:
        doc = await database.get(index=database.dbs.db_token, id=tid)
    except plugins.database.DBError:
        return False
    # Only allow a user to revoke their own tokens.
    if doc["_source"].get("cid") != cid:
        return False
    await database.delete(index=database.dbs.db_token, id=tid, refresh="wait_for")
    return True


async def lookup_token(database: plugins.database.Database, raw_token: str) -> typing.Optional[dict]:
    """Resolve a raw token to its stored doc, or None if missing/expired.

    Expired tokens are deleted as a side effect so they cannot be reused.
    """
    tid = hash_token(raw_token)
    try:
        doc = await database.get(index=database.dbs.db_token, id=tid)
    except plugins.database.DBError:
        return None
    src = doc["_source"]
    expires = src.get("expires") or 0
    if expires and int(time.time()) > expires:
        try:
            await database.delete(index=database.dbs.db_token, id=tid)
        except plugins.database.DBError:
            pass
        return None
    return src


async def touch_token(database: plugins.database.Database, tid: str, now: int) -> None:
    """Record that a token was just used (callers should throttle this)."""
    await database.update(index=database.dbs.db_token, id=tid, body={"doc": {"last_used": now}})


async def count_tokens(database: plugins.database.Database, cid: str) -> int:
    """Exact number of tokens owned by ``cid``.

    Used for enforcing the per-user cap: unlike list_tokens() this is not bounded
    by a search page size, so the cap holds even if it is configured above 100.
    """
    res = await database.count(index=database.dbs.db_token, body={"query": {"term": {"cid": cid}}})
    return int(res.get("count", 0))


async def purge_expired_tokens(database: plugins.database.Database, now: int) -> int:
    """Delete every token whose expiry has passed. Returns the number deleted.

    Tokens with ``expires == 0`` never expire and are left untouched. This is a
    housekeeping sweep so abandoned expired tokens do not accumulate in the
    index (they are also removed lazily by lookup_token on next use).
    """
    res = await database.delete_by_query(
        index=database.dbs.db_token,
        body={"query": {"range": {"expires": {"gt": 0, "lt": now}}}},
        conflicts="proceed",
        ignore=(404,),  # index may not exist yet; nothing to purge
    )
    return int(res.get("deleted", 0))


async def purge_tokens_for_cid(database: plugins.database.Database, cid: str) -> int:
    """Delete *every* token owned by account ``cid``. Returns the number deleted.

    Unlike revoke_token (which kills one specific token a user owns), this wipes
    an account's entire token set at once. It backs both the admin ``token_purge``
    action and the automatic revocation triggered when a user's upstream identity
    changes, so a token minted before a credential reset cannot outlive it.
    """
    if not cid:
        return 0
    res = await database.delete_by_query(
        index=database.dbs.db_token,
        body={"query": {"term": {"cid": cid}}},
        conflicts="proceed",
        ignore=(404,),  # index may not exist yet; nothing to purge
    )
    return int(res.get("deleted", 0))


# OAuth payload keys that vary between logins without reflecting a change in the
# user's identity or permissions (bearer/refresh secrets, token lifetimes, and
# per-exchange nonces). They are ignored when deciding whether a login
# represents a changed "setup", so an ordinary re-login does not needlessly
# invalidate a user's tokens.
_IDENTITY_VOLATILE_KEYS = frozenset(
    {
        "access_token",
        "refresh_token",
        "id_token",
        "token",
        "token_type",
        "expires",
        "expires_in",
        "exp",
        "iat",
        "nbf",
        "iss",
        "aud",
        "nonce",
        "state",
        "code",
        "scope",
        "session_state",
    }
)


def identity_fingerprint(oauth_data: typing.Any) -> str:
    """Stable digest of the identity-relevant parts of an OAuth payload.

    Everything the provider returns *except* the volatile secret/timestamp keys
    (see ``_IDENTITY_VOLATILE_KEYS``) is treated as identity: email, uid, and —
    crucially for permissions — any group/project/role membership the provider
    reports. Two payloads that describe the same person with the same
    entitlements therefore share a fingerprint even across separate logins.
    """
    if not isinstance(oauth_data, dict):
        oauth_data = {}
    material = {k: v for k, v in oauth_data.items() if k not in _IDENTITY_VOLATILE_KEYS}
    canonical = json.dumps(material, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def oauth_setup_changed(old_oauth_data: typing.Any, new_oauth_data: typing.Any) -> bool:
    """Whether a fresh OAuth login differs materially from the stored one.

    Used to auto-revoke tokens when the upstream account changes (e.g. a
    credential reset or a change in group membership). Errs toward *True*: any
    difference outside the volatile keys is treated as a change, so tokens are
    dropped rather than kept when in doubt.
    """
    return identity_fingerprint(old_oauth_data) != identity_fingerprint(new_oauth_data)
