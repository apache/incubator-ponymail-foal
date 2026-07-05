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

# To be run as: python3 -m pytest test/test_token.py
# This ensures sys.path is set up correctly.

import hashlib
import os
import sys

# The server imports its plugins as a top-level "plugins" package (it runs with
# the server/ directory as the working dir), so put server/ on the path here too.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "server"))

import plugins.token as token  # noqa: E402


class _FakeRequest:
    """Minimal stand-in for an aiohttp request exposing .headers.get()."""

    def __init__(self, headers=None):
        self.headers = headers or {}


def test_generate_token_is_prefixed_and_unique():
    a = token.generate_token()
    b = token.generate_token()
    assert a.startswith(token.TOKEN_PREFIX)
    assert b.startswith(token.TOKEN_PREFIX)
    assert a != b  # random -> effectively never collide
    # Prefix + url-safe secret should be comfortably long.
    assert len(a) > len(token.TOKEN_PREFIX) + 20


def test_hash_token_is_stable_sha256():
    raw = token.generate_token()
    assert token.hash_token(raw) == hashlib.sha256(raw.encode("utf-8")).hexdigest()
    # Same input -> same digest, different input -> different digest.
    assert token.hash_token(raw) == token.hash_token(raw)
    assert token.hash_token(raw) != token.hash_token(raw + "x")


def test_hash_token_does_not_contain_raw_secret():
    raw = token.generate_token()
    assert raw not in token.hash_token(raw)


def test_token_from_request_valid_bearer():
    raw = token.generate_token()
    req = _FakeRequest({"Authorization": "Bearer %s" % raw})
    assert token.token_from_request(req) == raw


def test_token_from_request_is_scheme_case_insensitive():
    raw = token.generate_token()
    req = _FakeRequest({"Authorization": "bearer %s" % raw})
    assert token.token_from_request(req) == raw


def test_token_from_request_rejects_missing_and_malformed():
    assert token.token_from_request(_FakeRequest({})) is None
    # No "Bearer " scheme
    assert token.token_from_request(_FakeRequest({"Authorization": "Basic abc"})) is None
    # Bearer but not one of our tokens (wrong prefix)
    assert token.token_from_request(_FakeRequest({"Authorization": "Bearer abc123"})) is None
    # Empty value
    assert token.token_from_request(_FakeRequest({"Authorization": ""})) is None


class _FakeSession:
    """Minimal stand-in for a SessionObject for scope checks."""

    def __init__(self, is_token, scopes=None):
        self.token = is_token
        self.token_scopes = scopes or []


def test_required_scope_maps_endpoints():
    assert token.required_scope("compose") == token.SCOPE_WRITE
    assert token.required_scope("mgmt") == token.SCOPE_ADMIN
    # Anything else is a read operation.
    for h in ("stats", "email", "thread", "mbox", "preferences", "unknown"):
        assert token.required_scope(h) == token.SCOPE_READ


def test_normalize_scopes_parsing_and_defaults():
    # String forms (space and comma separated) and lists all work.
    assert token.normalize_scopes("read write") == ["read", "write"]
    assert token.normalize_scopes("write,read") == ["read", "write"]  # canonical order
    assert token.normalize_scopes(["admin", "read"]) == ["read", "admin"]
    # Unknown scopes are dropped; duplicates collapsed.
    assert token.normalize_scopes("read read bogus") == ["read"]
    # Empty / invalid input falls back to the least-privilege default.
    assert token.normalize_scopes("") == list(token.DEFAULT_SCOPES)
    assert token.normalize_scopes("bogus") == list(token.DEFAULT_SCOPES)
    assert token.normalize_scopes(None) == list(token.DEFAULT_SCOPES)


def test_every_endpoint_scope_is_classified():
    """Guard against a new privileged endpoint being silently reachable by a
    read-only token. required_scope() defaults unlisted endpoints to read, so
    this test forces every endpoint to be classified on purpose: adding or
    removing an endpoint file fails here until this map (and, for write/admin
    endpoints, plugins/token.py) is updated.
    """
    endpoints_dir = os.path.join(os.path.dirname(__file__), os.pardir, "server", "endpoints")
    modules = {f[:-3] for f in os.listdir(endpoints_dir) if f.endswith(".py") and f != "__init__.py"}

    expected = {
        "compose": token.SCOPE_WRITE,
        "mgmt": token.SCOPE_ADMIN,
        "oauth": token.SCOPE_READ,  # public login handshake; no archive privilege
        "email": token.SCOPE_READ,
        "thread": token.SCOPE_READ,
        "source": token.SCOPE_READ,
        "mbox": token.SCOPE_READ,
        "stats": token.SCOPE_READ,
        "preferences": token.SCOPE_READ,
        "pminfo": token.SCOPE_READ,
        "gravatar": token.SCOPE_READ,
        "plain": token.SCOPE_READ,
        "token": token.SCOPE_READ,  # management endpoint; token auth is blocked inside it anyway
    }

    assert modules == set(expected), (
        "server/endpoints changed - classify the new/removed endpoint(s) in this test "
        "and (for write/admin endpoints) in plugins/token.py: %s" % (modules ^ set(expected))
    )
    for name, scope in expected.items():
        assert token.required_scope(name) == scope


def test_token_allows_enforces_scopes():
    # Cookie (non-token) sessions are never restricted here.
    assert token.token_allows(_FakeSession(False), "compose") is True
    assert token.token_allows(_FakeSession(False, []), "mgmt") is True

    read_only = _FakeSession(True, ["read"])
    assert token.token_allows(read_only, "stats") is True
    assert token.token_allows(read_only, "compose") is False
    assert token.token_allows(read_only, "mgmt") is False

    writer = _FakeSession(True, ["read", "write"])
    assert token.token_allows(writer, "compose") is True
    assert token.token_allows(writer, "mgmt") is False

    full = _FakeSession(True, list(token.ALL_SCOPES))
    assert all(token.token_allows(full, h) for h in ("stats", "compose", "mgmt"))


def test_token_cache_evicts_oldest_instead_of_flushing():
    import plugins.session as session  # noqa: E402

    cache: dict = {}
    for i in range(3):
        session._cache_put(cache, 3, "k%d" % i, {"n": i})
    assert list(cache) == ["k0", "k1", "k2"]

    # Over capacity -> evict the oldest entry only (k0), keep the rest.
    session._cache_put(cache, 3, "k3", {"n": 3})
    assert list(cache) == ["k1", "k2", "k3"]
    assert len(cache) == 3

    # Re-inserting an existing key refreshes its position to newest.
    session._cache_put(cache, 3, "k1", {"n": 11})
    assert list(cache) == ["k2", "k3", "k1"]
    assert cache["k1"] == {"n": 11}

    # ...so the next eviction drops k2, proving k1 was not treated as oldest.
    session._cache_put(cache, 3, "k4", {"n": 4})
    assert list(cache) == ["k3", "k1", "k4"]


def test_identity_fingerprint_ignores_volatile_keys():
    # Same person and permissions, but a fresh login returns new bearer secrets
    # and timestamps -> the fingerprint must stay identical so we don't purge
    # tokens on every ordinary re-login.
    base = {"uid": "alice", "email": "alice@example.org", "isMember": True, "projects": ["foo", "bar"]}
    login1 = {**base, "access_token": "aaa", "expires_in": 3600, "iat": 1000}
    login2 = {**base, "access_token": "zzz", "expires_in": 7200, "iat": 2000}
    assert token.identity_fingerprint(login1) == token.identity_fingerprint(login2)

    # Non-dict / empty inputs are handled and compare equal.
    assert token.identity_fingerprint(None) == token.identity_fingerprint({})


def test_oauth_setup_changed_detects_permission_changes():
    old = {"uid": "alice", "email": "alice@example.org", "projects": ["foo"], "access_token": "a"}

    # Pure re-login (only volatile fields differ) -> not a change.
    assert token.oauth_setup_changed(old, {**old, "access_token": "b", "iat": 42}) is False

    # Gained a project membership -> change.
    assert token.oauth_setup_changed(old, {**old, "projects": ["foo", "bar"]}) is True

    # Email changed -> change.
    assert token.oauth_setup_changed(old, {**old, "email": "alice@new.org"}) is True

    # A first-ever login (no prior data) counts as a change vs a populated payload.
    assert token.oauth_setup_changed({}, old) is True


def test_purge_tokens_for_cid():
    import asyncio

    class _FakeDBs:
        db_token = "ponymail-token"

    class _FakeDB:
        def __init__(self, deleted):
            self.dbs = _FakeDBs()
            self.calls = []
            self._deleted = deleted

        async def delete_by_query(self, index, body, **kwargs):
            self.calls.append({"index": index, "body": body, "kwargs": kwargs})
            return {"deleted": self._deleted}

    db = _FakeDB(deleted=3)
    n = asyncio.run(token.purge_tokens_for_cid(db, "cid123"))
    assert n == 3
    assert db.calls[0]["index"] == "ponymail-token"
    assert db.calls[0]["body"] == {"query": {"term": {"cid": "cid123"}}}

    # An empty cid must never issue a delete-everything query.
    db2 = _FakeDB(deleted=999)
    assert asyncio.run(token.purge_tokens_for_cid(db2, "")) == 0
    assert db2.calls == []
