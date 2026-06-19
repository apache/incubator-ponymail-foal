# Search Syntax Guide

This documents the user-facing search URLs used on lists.apache.org (and any
other PonyMail Foal instance). For the backend API, see `API.md`.

## URL Format

All search and list-browsing URLs follow this pattern:

```
https://<host>/list?<list>@<domain>:<date>:<query>
```

The three parts after `?` are separated by colons:

| Part | Required | Description |
|------|----------|-------------|
| `<list>@<domain>` | Yes | Which mailing list(s) to search |
| `<date>` | Optional | Time range to search within |
| `<query>` | Optional | Free-text search terms |

If you omit `<date>` and `<query>`, you get the default view (last 30 days,
no search filter).

---

## List Selection

| URL | Meaning |
|-----|---------|
| `list?dev@httpd.apache.org` | Only `dev@httpd.apache.org` |
| `list?*@httpd.apache.org` | All lists under `httpd.apache.org` |
| `list?dev@*` | All `dev@` lists across all domains |
| `list?*@*` | Everything (global search) |

---

## Date Ranges

The date segment (between the first and second colon) controls the time
window.

### Single month

```
https://lists.apache.org/list?dev@kafka.apache.org:2024-3
```
→ March 2024 only.

### Relative: "within the last…"

Use `lte=` followed by a number and time unit:

```
https://lists.apache.org/list?dev@kafka.apache.org:lte=30d
https://lists.apache.org/list?dev@kafka.apache.org:lte=2w
https://lists.apache.org/list?dev@kafka.apache.org:lte=6M
```

Time units: `d` (days), `w` (weeks), `M` (months), `y` (years).

### Relative: "older than…"

Use `gte=`:

```
https://lists.apache.org/list?user@spark.apache.org:gte=1y
```
→ Only emails older than 1 year.

### Specific day range

Use `dfr=` and `dto=` separated by a pipe:

```
https://lists.apache.org/list?user@spark.apache.org:dfr=2024-01-15|dto=2024-02-28
```
→ January 15 through February 28, 2024.

---

## Free-Text Search (the query segment)

The query appears after the second colon.

### Single-word search

```
https://lists.apache.org/list?dev@httpd.apache.org:lte=1M:VOTE
```
→ Emails from the last month containing "VOTE" in from, subject, or body.

### Multiple terms (AND)

Multiple terms are ANDed — all must appear (in any of from, subject, or body):

```
https://lists.apache.org/list?dev@lucene.apache.org:lte=3M:release%20candidate
```
→ Emails containing both "release" and "candidate" (each may appear in any
field — from, subject, or body).

**Important:** Spaces in the query must be encoded as `%20` in URLs. A
literal space will break the URL.

### Excluding terms

Prefix a term with `-` to exclude emails containing it:

```
https://lists.apache.org/list?dev@flink.apache.org:lte=6M:release%20-test
```
→ Emails containing "release" but NOT "test".

### Searching for a literal dash

Double the dash (`--`) to escape it:

```
https://lists.apache.org/list?dev@flink.apache.org:lte=1y:---1
```
→ Finds emails containing the literal string "-1".

### Exact phrases

Wrap in quotes (URL-encode the quotes as `%22`):

```
https://lists.apache.org/list?dev@lucene.apache.org:lte=6M:%22release%20candidate%22
```

Note: phrase matching may not behave differently from a multi-word AND search
in all cases.

---

## Header Filters

You can filter by specific email headers by appending `&header_<field>=<value>`
after the colon-separated portion:

| Parameter | Searches |
|-----------|----------|
| `&header_from=` | The `From:` header |
| `&header_subject=` | The `Subject:` header |
| `&header_to=` | The `To:` header |
| `&header_body=` | The message body |
| `&header_messageid=` | The `Message-ID:` header |

These use phrase matching — the value must appear as a contiguous phrase.

Example — find emails from "Jim Jagielski" on `dev@community.apache.org` in
March 2024:

```
https://lists.apache.org/list?dev@community.apache.org:2024-3:&header_from=Jim Jagielski
```

Example — search for a specific Message-ID:

```
https://lists.apache.org/list?dev@tomcat.apache.org::&header_messageid=abc123@example.com
```

(Note the empty date and query segments — just two colons before `&header_*`.)

---

## Complete Examples

| Goal | URL |
|------|-----|
| Browse dev@httpd last 30 days | `list?dev@httpd.apache.org` |
| VOTE threads this month | `list?dev@httpd.apache.org:lte=1M:VOTE` |
| All Kafka lists, last 6 months, about "rebalance" | `list?*@kafka.apache.org:lte=6M:rebalance` |
| Emails from Jane on Flink user list | `list?user@flink.apache.org::&header_from=Jane Smith` |
| Emails about releases (not tests) on Flink | `list?dev@flink.apache.org:lte=6M:release%20-test` |

---

## Notes

- Search matches against **from**, **subject**, and **body** — not just subject.
- All positive terms are ANDed — every term must appear somewhere across those
  three fields.
- Negation (`-word`) excludes the email if the word appears in any of the
  three fields.
- Colons in search terms are stripped (they conflict with the URL format
  delimiter).
- Spaces in the query segment must be encoded as `%20` in URLs.
- If no date is specified, the default is the last 30 days.
