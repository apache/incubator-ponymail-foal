<!---
 Licensed to the Apache Software Foundation (ASF) under one or more
 contributor license agreements.  See the NOTICE file distributed with
 this work for additional information regarding copyright ownership.
 The ASF licenses this file to You under the Apache License, Version 2.0
 (the "License"); you may not use this file except in compliance with
 the License.  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
-->

# asfquart / ATR Alignment and Future Migration

This note explains how Foal's long-term [API tokens](API.md#authentication) relate
to the token/authentication model used by
[asfquart](https://github.com/apache/infrastructure-asfquart) — the framework
several ASF Tooling and Infrastructure web apps are built on — and by
[ATR (`apache/tooling-trusted-releases`)](https://github.com/apache/tooling-trusted-releases),
which builds a full token subsystem on top of asfquart.

It has two purposes:

1. **Mirror the semantics** so that Foal's tokens are conceptually compatible with
   asfquart/ATR today, without taking a Quart dependency.
2. **Record the migration steps** should Foal ever move onto Quart/asfquart.

A small, tested reference implementation of the mapping lives in
[`server/plugins/asfquart_compat.py`](../server/plugins/asfquart_compat.py). It is
**not** wired into the request path — it exists to keep the translation honest and
in one reviewed place.

## What asfquart actually provides

asfquart is *not* a token manager. It provides the authentication **seam** and the
authorization **vocabulary**:

- A **bearer hook**: `session.py` turns an `Authorization: Bearer <token>` header
  into a session by calling a pluggable `app.token_handler(token)` callback that
  the application supplies. asfquart itself does not generate, store, expire, or
  revoke tokens.
- A **session shape** (`asfquart.session.ClientSession`): `uid`, `email`,
  `fullname`, `isMember` / `isChair` / `isRoot`, `pmcs`, `projects`, `mfa`,
  `roleaccount`, and a free-form `metadata` dict. By convention (see asfquart's
  `personal_access_tokens.py` example, which ATR follows) a token's scope lives at
  `metadata["scope"]`.
- **Requirement decorators**: `@asfquart.auth.require(Requirements.member)` etc.,
  where each requirement is `fn(client_session) -> (passes, message)`, combinable
  with `all_of` / `any_of`.

Everything else — generation, hashed storage, expiry, per-user caps, scope
intersection, admin/auto revocation, audit — is application code. In asfquart-land
that machinery currently lives in **ATR**, not in asfquart. Foal implements its own
equivalent (see [`plugins/token.py`](../server/plugins/token.py)); the two are
parallel implementations of the same idea on different web stacks (ATR on Quart,
Foal on `aiohttp`).

### Design difference worth knowing

ATR issues a long-lived Personal Access Token that is exchanged for a short-lived
(30-minute, HS256) JWT which authenticates each API call. Foal uses the opaque
token **directly** on every request and re-intersects its scope with the owner's
**current** account permissions server-side each time. Both are valid; they trade
off differently on revocation latency vs. per-request cost. Foal's model needs no
token exchange endpoint and revokes effectively immediately; ATR's JWT avoids a
token lookup per call at the cost of a short revocation delay.

## Semantic mapping

| Foal (`SessionObject` / `plugins.token`)      | asfquart / ATR                                 | Notes |
|-----------------------------------------------|------------------------------------------------|-------|
| `credentials.uid`                             | `uid`                                          | |
| `credentials.email`                           | `email`                                        | |
| `credentials.name`                            | `fullname`                                     | |
| `credentials.admin`                           | `isRoot`                                        | Closest analogue to infra-root membership. |
| `session.token` (Bearer auth)                 | `roleaccount`                                   | asfquart's PAT example models tokens as role accounts. |
| `session.token_scopes`                        | `metadata["scope"]`                            | Same key asfquart reads. |
| `token.required_scope(handler)`               | a `Requirements`-style predicate               | See `scope_requirement()`. |
| `token.token_allows(session, handler)`        | `@asfquart.auth.require(...)`                   | Same allow/deny outcome. |
| *(not tracked)*                               | `isMember`, `isChair`, `pmcs`, `projects`, `mfa` | Foal does not model ASF org roles; a Quart deployment would fill these from the OAuth payload. |

`scope_requirement(scope)` returns a predicate shaped exactly like an
`asfquart.auth.Requirements` member, so the per-endpoint rule enforced today in
`main.py` via `token.token_allows(...)` could instead be attached declaratively:

```python
@asfquart.auth.require(scope_requirement(token.required_scope(handler)))
async def handler(...):
    ...
```

An interactive (cookie) session is rendered with all scopes, so it satisfies every
requirement — matching today's rule that only token sessions are scope-restricted.

The mapping is covered by [`test/test_asfquart_compat.py`](../test/test_asfquart_compat.py),
which asserts that `scope_requirement` agrees with `token.token_allows` for every
endpoint/scope pairing, so the two never drift.

## Future migration steps (should Foal move to Quart/asfquart)

Foal's server is a hand-rolled `aiohttp` application, so adopting asfquart is a
reframing, not a drop-in. If that is ever undertaken, the token work done here is
designed to make it incremental:

1. **Add the dependency** and stand up an asfquart `APP` alongside (or in front of)
   the existing server, sharing the OpenSearch backend.
2. **Register a `token_handler`** that calls the existing
   `plugins.token.lookup_token()` and returns `asfquart_compat.to_asfquart_session()`
   for the resolved account. This reuses generation/storage/expiry/revocation
   unchanged — only the *presentation* of the session changes.
3. **Populate the org-role fields** (`isMember`, `isChair`, `pmcs`, `projects`,
   `mfa`) from the OAuth payload Foal already receives, so asfquart's
   `Requirements` gain real backing data instead of the empty defaults.
4. **Replace the central scope check** in `main.py` with per-endpoint
   `@asfquart.auth.require(scope_requirement(...))` decorators. Because the
   predicate already mirrors `token_allows`, this is a mechanical move with no
   behavioural change.
5. **Consider aligning revocation** with any shared asfquart/ATR token layer if one
   materialises upstream (ATR's admin purge / banning) — Foal's `purge_tokens_for_cid`
   and OAuth-fingerprint auto-revocation are the natural integration points.
6. **Optionally adopt the PAT→JWT exchange** if per-request token lookups become a
   bottleneck; until then Foal's direct-token model keeps revocation immediate.

Steps 2–4 can land independently and be reverted independently, so the migration
need not be a single big-bang change.
