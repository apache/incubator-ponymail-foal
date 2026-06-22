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

| Index | Purpose |
|-------|---------|
| `ponymail-mbox` | Parsed email metadata (from, subject, date, body, list-id, threading info) |
| `ponymail-source` | Raw RFC 2822 email source (the original message as received) |
| `ponymail-attachment` | Binary attachment data |
| `ponymail-account` | User session/preference data |
| `ponymail-session` | Active login sessions (cookie ↔ account mapping) |
| `ponymail-notification` | Per-user notifications for watched threads |
| `ponymail-auditlog` | Admin action audit trail |

The definitive field mappings are in `tools/mappings.yaml` (used by
`setup.py` to create indices). Below is a summary of the key fields.

---

## Data Model

### Email Document (`mbox` index)

| Field | Type | Description |
|-------|------|-------------|
| `mid` | keyword | Internal permalink ID (DKIM-based). Also the document `_id` |
| `dbid` | keyword | SHA3-256 of the raw source. Also the `_id` in the source index |
| `message-id` | keyword | Original Message-ID header |
| `from` | text | Sender display (searchable) |
| `from_raw` | keyword | Sender address (exact match) |
| `to` | text | Recipient(s) |
| `cc` | text | CC recipients |
| `subject` | text | Subject line (`fielddata: true` for aggregations/word cloud) |
| `body` | text | Parsed plain-text body |
| `body_short` | text | First ~200 characters of body |
| `date` | date | UTC datetime (`yyyy/MM/dd HH:mm:ss`) |
| `epoch` | long | Unix timestamp parsed from Date: header |
| `list` | text | List-ID header (searchable) |
| `list_raw` | keyword | List-ID header (exact match, format: `<list.domain>`) |
| `forum` | keyword | List address as `list@domain` |
| `in-reply-to` | keyword | In-Reply-To header (for threading) |
| `references` | text | References header chain |
| `private` | boolean | Whether this email is on a private list |
| `deleted` | boolean | Soft-delete flag (hidden from UI) |
| `attachments` | nested | Array: `{filename, content_type, hash, size}` |
| `gravatar` | text | MD5 of sender address for avatar lookup |
| `permalinks` | keyword[] | All IDs this email is accessible under |
| `size` | long | Size of raw source in bytes |
| `html_source_only` | boolean | Body stored as HTML (html2text unavailable at archive time) |
| `_notes` | text | Internal annotations |
| `_archived_at` | long | Epoch when the email was archived |

**Threading fields** (only present when `archiver.threadinfo` is enabled):

| Field | Type | Description |
|-------|------|-------------|
| `top` | boolean | Is this email the root of a thread? |
| `thread` | keyword | Permalink ID of the thread root |
| `previous` | keyword | Permalink ID of the parent message |

### Source Document (`source` index)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | — | Same as `dbid` in the mbox entry |
| `source` | binary | The complete raw RFC 2822 message |
| `message-id` | keyword | Original Message-ID (for cross-reference) |
| `deleted` | boolean | Soft-delete flag |

### Attachment Document (`attachment` index)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | — | The attachment `hash` from the mbox entry |
| `source` | binary | Raw attachment binary data |

### Account Document (`account` index)

| Field | Type | Description |
|-------|------|-------------|
| `cid` | keyword | Account ID |
| `credentials.email` | keyword | OAuth-provided email |
| `credentials.name` | keyword | OAuth-provided display name |
| `credentials.uid` | keyword | OAuth-provided user ID |
| `internal.admin` | boolean | Has admin privileges |
| `internal.oauth_provider` | keyword | Which OAuth provider authenticated this user |
| `internal.oauth_data` | object | Provider-specific data (dynamic) |
| `request_id` | keyword | Session correlation ID |

### Session Document (`session` index)

| Field | Type | Description |
|-------|------|-------------|
| `cookie` | keyword | Session cookie value |
| `cid` | keyword | Linked account ID |
| `updated` | long | Last activity epoch |

### Notification Document (`notification` index)

| Field | Type | Description |
|-------|------|-------------|
| `recipient` | keyword | Email address of the user to notify |
| `mid` | text | Message permalink ID |
| `message-id` | keyword | Original Message-ID |
| `from` | text | Sender of the triggering message |
| `subject` | keyword | Subject line |
| `list` | text | List-ID |
| `date` | date | Message date |
| `epoch` | long | Message epoch |
| `private` | boolean | Whether the message is private |
| `seen` | long | Epoch when the notification was marked read (0 = unseen) |
| `type` | keyword | Notification type |

### Audit Log Document (`auditlog` index)

| Field | Type | Description |
|-------|------|-------------|
| `date` | date | When the action was performed |
| `author` | keyword | Admin who performed the action |
| `remote` | keyword | Remote IP address |
| `action` | keyword | Action type (edit, delete, hide, unhide) |
| `target` | keyword | Document ID affected |
| `lid` | keyword | List-ID context |
| `log` | text | Description of what was changed |

---

### Threading Model

Threading is reconstructed at query time from `in-reply-to` and
`references` headers. The `thread.json` endpoint walks up/down the
chain to build a tree structure. When `archiver.threadinfo` is enabled,
pre-computed `top`, `thread`, and `previous` fields accelerate lookups.

---

## Request Lifecycle

1. **Client** sends request to reverse proxy (e.g. `GET /api/stats.lua?list=dev&domain=httpd.apache.org`)
2. **Proxy** forwards `/api/*` to the aiohttp server on port 8080
3. **`main.py` routing**:
   - Strips suffix (`.lua` → form parsing, `.json` → JSON parsing)
   - Looks up handler name in `self.handlers` dict
   - Acquires a database connection from the async pool
   - Creates a session object (validates cookie if present)
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
| `session.py` | Cookie management, OAuth credential tracking |
| `aaa.py` | Access control (public vs private list checks) |
| `defuzzer.py` | Date/query parameter normalization and validation |
| `background.py` | Periodic tasks (refresh list counts, activity stats) |
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
