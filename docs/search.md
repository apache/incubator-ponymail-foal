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

You can also view multiple specific lists by comma-separating them:

```
https://lists.apache.org/list?dev@tomcat.apache.org,users@tomcat.apache.org
```

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

### Basic terms

```
https://lists.apache.org/list?dev@httpd.apache.org:lte=1M:VOTE
```
→ Emails from the last month containing "VOTE" in from, subject, or body.

### Multiple terms (AND)

All terms must match (but not necessarily as a contiguous phrase):

```
https://lists.apache.org/list?dev@lucene.apache.org:lte=3M:release candidate
```
→ Emails containing both "release" and "candidate" (anywhere in from/subject/body).

### Exact phrase

Wrap in quotes **in the search box**:

    "release candidate"

This finds emails containing the exact contiguous phrase. Note that quoted
phrases work reliably when typed into the search box, but may not work when
pasted directly into a URL (browsers may mangle the quote characters).

### Excluding terms

Prefix with `-`:

```
https://lists.apache.org/list?dev@flink.apache.org:lte=6M:release -test
```
→ Emails containing "release" but NOT "test".

### Searching for a literal dash

Double the dash (`--`) to escape it:

```
https://lists.apache.org/list?dev@flink.apache.org:lte=1y:---1
```
→ Finds emails containing the literal string "-1".

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
| Release announcements on Lucene, last 6 months | `list?dev@lucene.apache.org:lte=6M:release announcement` |

---

## Notes

- All positive search terms are ANDed — every term must appear somewhere in
  the from, subject, or body fields.
- Negation (`-word`) excludes the email if the word appears in *any* of
  from, subject, or body.
- Colons in search terms are stripped (they conflict with the URL format
  delimiter).
- Multi-word queries (including quoted phrases) may not work reliably when
  combined with the `dfr=|dto=` day-range format. Use `lte=` or single-month
  dates if your query contains spaces.
- If no date is specified, the default is the last 30 days.
