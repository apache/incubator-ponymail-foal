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

# To be run as: python3 -m pytest test/test_asfquart_compat.py
# This ensures sys.path is set up correctly.

import os
import sys

# The server imports its plugins as a top-level "plugins" package (it runs with
# the server/ directory as the working dir), so put server/ on the path here too.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "server"))

import plugins.asfquart_compat as compat  # noqa: E402
import plugins.token as token  # noqa: E402


class _FakeCreds:
    def __init__(self, uid="", name="", email="", admin=False, authoritative=False, oauth_provider=""):
        self.uid = uid
        self.name = name
        self.email = email
        self.admin = admin
        self.authoritative = authoritative
        self.oauth_provider = oauth_provider


class _FakeSession:
    """Minimal stand-in for a SessionObject."""

    def __init__(self, is_token, scopes=None, credentials=None):
        self.token = is_token
        self.token_scopes = scopes or []
        self.credentials = credentials


def test_token_session_maps_to_asfquart_shape():
    creds = _FakeCreds(uid="alice", name="Alice A", email="alice@apache.org", oauth_provider="google")
    session = _FakeSession(True, ["read", "write"], creds)
    out = compat.to_asfquart_session(session)

    # Identity fields carry across.
    assert out["uid"] == "alice"
    assert out["fullname"] == "Alice A"
    assert out["email"] == "alice@apache.org"
    # A token session is modelled as a role account (matches asfquart's PAT example).
    assert out["roleaccount"] is True
    # Scopes live under metadata["scope"] exactly like asfquart expects.
    assert out["metadata"][compat.SCOPE_METADATA_KEY] == ["read", "write"]
    assert out["metadata"]["api_token"] is True
    assert out["metadata"]["oauth_provider"] == "google"


def test_interactive_session_is_unrestricted_and_not_a_roleaccount():
    creds = _FakeCreds(uid="bob", email="bob@apache.org", admin=True)
    session = _FakeSession(False, credentials=creds)
    out = compat.to_asfquart_session(session)

    assert out["roleaccount"] is False
    # An interactive session is not scope-restricted -> all scopes present.
    assert out["metadata"][compat.SCOPE_METADATA_KEY] == list(token.ALL_SCOPES)
    # PonyMail "admin" maps to asfquart's isRoot, the closest analogue.
    assert out["isRoot"] is True


def test_missing_credentials_yield_empty_but_valid_shape():
    out = compat.to_asfquart_session(_FakeSession(False, credentials=None))
    assert out["uid"] == ""
    assert out["email"] == ""
    assert out["isRoot"] is False
    # Even with no credentials the required asfquart keys exist.
    for key in ("uid", "email", "fullname", "isMember", "isChair", "isRoot", "roleaccount", "metadata"):
        assert key in out


def test_scope_requirement_mirrors_token_allows():
    # For a token session, the asfquart-style requirement must agree with the
    # native token.token_allows() decision for every endpoint/scope pairing.
    for scopes in ([], ["read"], ["read", "write"], list(token.ALL_SCOPES)):
        session = _FakeSession(True, scopes)
        asf = compat.to_asfquart_session(session)
        for handler in ("stats", "compose", "mgmt"):
            required = token.required_scope(handler)
            passes, message = compat.scope_requirement(required)(asf)
            assert passes == token.token_allows(session, handler)
            if not passes:
                assert required in message


def test_scope_requirement_predicate_is_named():
    # asfquart derives error routing from the requirement's __name__; make sure
    # ours is stable and scope-specific rather than the generic closure name.
    req = compat.scope_requirement("admin")
    assert req.__name__ == "scope_admin"
