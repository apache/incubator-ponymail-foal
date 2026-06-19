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

# Admin Guide

## Enabling Administration

Two configuration steps are required in `server/ponymail.yaml`:

1. Enable the management console:

```yaml
ui:
  mgmtconsole: true
```

2. Define admin users (must authenticate via an authoritative OAuth provider):

```yaml
oauth:
  authoritative_domains:
    - googleapis.com
  admins:
    - admin@example.org
    - another-admin@example.org
```

Restart the server after changes.

---

## Management Console

Admin users see a yellow cog icon in the context menu of each email.
Clicking it opens the management interface for that message.

### Available Actions

| Action | Effect |
|--------|--------|
| **Hide** | Marks the email as hidden. It remains in OpenSearch but is not shown to users. Recoverable. |
| **Unhide** | Restores a previously hidden email. |
| **Delete** | Permanently removes the email from both `mbox` and `source` indices. Only available when `allow_delete: true`. Irreversible. |
| **Edit** | Change metadata (e.g. move to different list-ID). |

### GDPR Compliance

For full GDPR compliance (right to erasure), set:

```yaml
ui:
  mgmtconsole: true
  allow_delete: true
```

When `allow_delete` is `true`:
- "Delete" fully expunges the email from OpenSearch (both `mbox` and `source` indices)
- The deletion is logged in the audit trail
- The email cannot be recovered

When `allow_delete` is `false` (default):
- "Delete" merely hides the email (sets a hidden flag)
- An admin can unhide it later
- The raw source remains in the `source` index

---

## Audit Log

All admin actions are logged. View the audit log via the API:

```bash
curl -X POST https://your-instance/api/mgmt.json \
  -H "Content-Type: application/json" \
  -H "Cookie: ponymail=your-session-cookie" \
  -d '{"action": "log", "size": 50, "page": 0}'
```

Or filter by action type:

```bash
curl -X POST https://your-instance/api/mgmt.json \
  -H "Content-Type: application/json" \
  -H "Cookie: ponymail=your-session-cookie" \
  -d '{"action": "log", "filter": "delete"}'
```

---

## Command-Line Tools

### Bulk Edit (`tools/bulk-edit.py`)

Perform batch metadata changes across many emails. Useful for:
- Moving emails to a different list-ID after a list rename
- Bulk privacy changes

### Re-threading (`tools/rethread.py`)

Recompute threading metadata for all emails. Run this after:
- Importing mbox files that arrived out of order
- Enabling `archiver.threadinfo` after initial import

```bash
cd tools
python3 rethread.py
```

### Re-indexing

If you need to rebuild the OpenSearch indices from scratch:

1. Back up your data
2. Delete the indices: `curl -X DELETE http://localhost:9200/ponymail-*`
3. Re-run setup: `python3 tools/setup.py`
4. Re-import all mbox files: `python3 tools/import-mbox.py --source /path/to/archives/`

---

## Monitoring

### Check Server Health

```bash
curl -s http://localhost:8080/api/pminfo.json | python3 -m json.tool
```

### Check OpenSearch Index Sizes

```bash
curl -s http://localhost:9200/_cat/indices/ponymail-*?v
```

### Common Issues

| Symptom | Likely Cause |
|---------|-------------|
| 404 on all API calls | Server not running or proxy misconfigured |
| Empty list overview | Background refresh hasn't run yet (wait `refresh_rate` seconds) |
| Private emails visible without login | `authoritative_domains` not set, or AAA plugin bypassed |
| "API error occurred" with traceback | Set `ui.traceback: false` in production, check journal for details |
| Compose/reply silently fails | Check `ui.mailhost` and `ui.sender_domains` config |
