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

# Architecture Overview

## Component Diagram

```
                          ┌─────────────────────┐
                          │   Mailing List MTA   │
                          │  (Postfix / ezmlm)   │
                          └──────────┬──────────┘
                                     │ pipe via /etc/aliases
                                     ▼
                          ┌─────────────────────┐
                          │  tools/archiver.py   │
                          │  (Email ingestion)   │
                          └──────────┬──────────┘
                                     │ index
                                     ▼
┌──────────────┐         ┌─────────────────────┐         ┌──────────────┐
│   Browser    │◄───────►│   OpenSearch   │◄───────►│ tools/*.py   │
│              │         │   (Data store)        │         │ (import,     │
└──────┬───────┘         └──────────▲──────────┘         │  migrate,    │
       │                            │                     │  rethread)   │
       │ HTTP                       │ async queries       └──────────────┘
       ▼                            │
┌──────────────┐         ┌──────────┴──────────┐
│  httpd/nginx │────────►│  server/main.py      │
│  (reverse    │  proxy  │  (aiohttp API)       │
│   proxy)     │  /api/  │                      │
└──────┬───────┘         └─────────────────────┘
       │
       │ static files
       ▼
┌──────────────┐
│   webui/     │
│ (JS + HTML)  │
└──────────────┘
```

## Components

### Email Ingestion (`tools/`)

- **`archiver.py`** — Called by the MTA (via `/etc/aliases`) for each
  incoming email. Parses the message, generates a DKIM-based permalink
  ID, stores the parsed email in the `mbox` index and the raw source in
  the `source` index.
- **`import-mbox.py`** — Bulk imports existing mbox files into OpenSearch.
- **`migrate.py`** — Migrates databases from the older Lua-based PonyMail.
- **`rethread.py`** — Recomputes threading metadata for existing emails.
- **`setup.py`** — First-time OpenSearch index creation with correct mappings.

### API Server (`server/`)

An async Python HTTP server built on **aiohttp**. Handles all API
requests, manages sessions, and queries OpenSearch.

- Listens on a configurable port (default 8080)
- Placed behind a reverse proxy (httpd or nginx) that serves the static
  UI and forwards `/api/` requests to the server

### Web UI (`webui/`)

A static JavaScript/HTML frontend. No build step required for deployment
— just serve the directory. Source JS files in `webui/js/source/` are
concatenated into `webui/js/ponymail.js` via `build.sh` during development.

### OpenSearch

The sole data store. Contains these indices (prefixed by `db_prefix`,
default `ponymail`):

| Index | Content |
|-------|---------|
| `ponymail-mbox` | Parsed email metadata (from, subject, date, body, list-id, threading info) |
| `ponymail-source` | Raw RFC 2822 email source (the original message as received) |
| `ponymail-account` | User session/preference data |
| `ponymail-token` | Long-term API tokens (SHA-256 hash, owner, scopes, expiry) |
| `ponymail-auditlog` | Admin action audit trail |

---

## Data Model

### Email Document (`mbox` index)

Each email is stored with:

- `mid` — Internal permalink ID (DKIM-based, collision-resistant)
- `dbid` — SHA3-256 of the raw message source
- `message-id` — Original Message-ID header
- `from`, `to`, `cc`, `subject`, `date`, `epoch`
- `body` — Parsed plain-text body
- `list` / `list_raw` — List-ID header
- `in-reply-to`, `references` — Threading headers
- `private` — Whether the email is on a private list
- `attachments` — Array of attachment metadata (filename, hash, size)
- `gravatar` — MD5 of sender address for avatar lookup

### Source Document (`source` index)

- `id` — Same `dbid` as the corresponding mbox entry
- `source` — The complete raw RFC 2822 message

### Threading

Threading is reconstructed at query time from `in-reply-to` and
`references` headers. The `thread.json` endpoint walks up/down the
chain to build a tree structure.

Optional threading metadata (enabled via `archiver.threadinfo` config):
- `top` — Boolean: is this email the root of a thread?
- `thread` — ID of the thread root
- `previous` — ID of the parent message

---

## Request Lifecycle

1. **Client** sends request to reverse proxy (e.g. `GET /api/stats.lua?list=dev&domain=httpd.apache.org`)
2. **Proxy** forwards `/api/*` to the aiohttp server on port 8080
3. **`main.py` routing**:
   - Strips suffix (`.lua` → form parsing, `.json` → JSON parsing)
   - Looks up handler name in `self.handlers` dict
   - Acquires a database connection from the async pool
   - Creates a session object (validates the cookie or, for programmatic
     clients, an `Authorization: Bearer` API token if present)
4. **Endpoint** `process(server, session, indata)` executes:
   - Builds OpenSearch query via `plugins.defuzzer` (normalizes dates/filters)
   - Checks access via `plugins.aaa` (private list filtering)
   - Queries OpenSearch via `session.database`
   - Returns a dict (auto-serialized to JSON) or a custom `aiohttp.web.Response`
5. **Response** sent back through proxy to client

---

## Server Plugin Architecture

Plugins in `server/plugins/` are shared internal modules — not
user-installable extensions.

| Plugin | Role |
|--------|------|
| `configuration.py` | YAML config parsing (all config keys defined here) |
| `database.py` | Async OpenSearch client, connection pool, index names |
| `messages.py` | Email retrieval, threading logic, access filtering, trimming |
| `session.py` | Cookie management, API token authentication, OAuth credential tracking |
| `aaa.py` | Access control (public vs private list checks) |
| `defuzzer.py` | Date/query parameter normalization and validation |
| `background.py` | Periodic tasks (refresh list counts, activity stats, purge expired API tokens) |
| `token.py` | API token generation, SHA-256 hashing, per-action scopes, expiry |
| `formdata.py` | Request body parsing (form-encoded vs JSON) |
| `offloader.py` | Thread pool executor for CPU-bound JSON serialization |
| `auditlog.py` | Admin action audit trail |
| `server.py` | Base classes: `Endpoint`, `StreamingEndpoint`, `BaseServer` |
| `oauthGeneric.py` | Generic OAuth token exchange |
| `oauthGoogle.py` | Google-specific OAuth (ID token verification) |
| `oauthGithub.py` | GitHub OAuth (code → token → user info) |

## Tools Plugin Architecture

Plugins in `tools/plugins/` support the archiver and import tools:

| Plugin | Role |
|--------|------|
| `elastic.py` | Synchronous OpenSearch client for CLI tools |
| `generators.py` | Email ID generation strategies |
| `dkim_id.py` | DKIM-based permalink generation (collision-resistant) |
| `textlib.py` | Text normalization, List-ID parsing |
| `mboxo_patch.py` | Workarounds for mbox format edge cases |
| `ponymailconfig.py` | INI-style config parser for `archiver.yaml` |
