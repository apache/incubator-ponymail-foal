# Search Syntax Guide

PonyMail Foal's search has two layers:

1. **The search box** — where you type free-text queries.
2. **URL parameters** — which encode header filters, date ranges, and list
   scope. The UI sets these for you, but you can also construct URLs directly.

---

## The Search Box (free-text query)

Type in the main search box. Terms are matched against the **from**,
**subject**, and **body** fields of each email.

| Syntax | Meaning | Example |
|--------|---------|---------|
| `word` | Email must contain this word | `release` |
| `"exact phrase"` | Email must contain this exact phrase | `"next release"` |
| `word1 word2` | Email must contain **both** words (AND) | `release candidate` |
| `-word` | Exclude emails containing this word | `-spam` |
| `--word` | Search for a literal leading dash | `---1` finds `-1` |

**Notes:**

- All positive terms are ANDed — every term must appear somewhere in from,
  subject, or body.
- Negation (`-word`) excludes the email if the word appears in *any* of the
  three fields.
- Colons are stripped, so Lucene-style `field:value` syntax does not work in
  the search box.

The free-text query appears in the URL as the `q=` parameter:

```
/api/stats.json?q=release+candidate&list=dev&domain=kafka.apache.org
```

---

## Header Filters (advanced search form → URL parameters)

The advanced search form provides separate input fields that map to URL
parameters:

| Form field | URL parameter | Searches | Match type |
|------------|---------------|----------|------------|
| From | `header_from=` | `From:` header | phrase |
| Subject | `header_subject=` | `Subject:` header | phrase |
| To | `header_to=` | `To:` header | phrase |
| Body | `header_body=` | message body | phrase |
| Message-ID | `header_messageid=` | `Message-ID:` header | phrase |

These combine with the free-text query. Example — find emails from "Jane
Smith" containing "release":

```
/api/stats.json?q=release&header_from=Jane+Smith&list=dev&domain=spark.apache.org
```

---

## Date Ranges (URL parameters)

By default, results cover the **last 30 days**. The date range is controlled
by URL parameters — the UI date picker sets them for you.

### Single month (`d=YYYY-MM`)

Show only emails from one calendar month.

```
/api/stats.json?d=2024-3&list=dev&domain=tomcat.apache.org
```

### Month range (`s=` and `e=`)

Start and end months (inclusive).

```
/api/stats.json?s=2024-1&e=2024-6&list=dev&domain=tomcat.apache.org
```
→ January through June 2024.

### Relative: "within the last…" (`d=lte=`)

```
/api/stats.json?d=lte%3D30d&list=dev&domain=lucene.apache.org   → last 30 days
/api/stats.json?d=lte%3D2w&list=dev&domain=lucene.apache.org    → last 2 weeks
/api/stats.json?d=lte%3D6M&list=dev&domain=lucene.apache.org    → last 6 months
```

### Relative: "older than…" (`d=gte=`)

```
/api/stats.json?d=gte%3D1y&list=dev&domain=lucene.apache.org    → older than 1 year
```

Time units: `d` (days), `w` (weeks), `M` (months), `y` (years).

### Specific day range (`d=dfr=...|dto=...`)

```
/api/stats.json?d=dfr%3D2024-01-15%7Cdto%3D2024-02-28&list=user&domain=flink.apache.org
```
→ January 15 through February 28, 2024.

### Days-ago span (`dfrom=` and `dto=`)

`dfrom` = how many days ago to start; `dto` = how many days to span forward
from that point.

```
/api/stats.json?dfrom=90&dto=30&list=user&domain=flink.apache.org
```
→ From 90 days ago to 60 days ago (a 30-day window).

---

## Search Scope (URL parameters)

Controls which mailing lists are searched.

| Scope | URL | Meaning |
|-------|-----|---------|
| Single list | `list=dev&domain=httpd.apache.org` | Only `dev@httpd.apache.org` |
| Whole domain | `list=*&domain=httpd.apache.org` | All lists under `httpd.apache.org` |
| Single list name, all domains | `list=dev&domain=*` | `dev@` everywhere |
| Global | `list=*&domain=*` | All lists, all domains |

The scope selector next to the search box sets `list` and `domain` for you.

---

## Putting It All Together

Find emails about "TLS" on all httpd lists, from the last 6 months, excluding
test noise:

```
/api/stats.json?q=TLS+-test&d=lte%3D6M&list=*&domain=httpd.apache.org
```

Find emails from "Jim Jagielski" on `dev@community.apache.org` in March 2024:

```
/api/stats.json?q=&header_from=Jim+Jagielski&d=2024-3&list=dev&domain=community.apache.org
```
