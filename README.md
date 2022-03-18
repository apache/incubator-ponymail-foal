# Apache Pony Mail Foal
<img src="https://github.com/apache/incubator-ponymail-foal/blob/master/webui/images/foal.png" width="72" align="left"/>

_Next generation suite of services and tools for Apache Pony Mail (incubating)_

| Type tests: | ![CI Status, Type Tests](https://img.shields.io/github/workflow/status/apache/incubator-ponymail-foal/Foal%20Type%20Tests?style=plastic) |
|-----|-------|
| **Unit tests:** | ![CI Status, Unit Tests](https://img.shields.io/github/workflow/status/apache/incubator-ponymail-foal/Unit%20Tests?style=plastic) |


This repository aims to contain the next generation of Apache Pony Mail,
a pure Python version of Apache Pony Mail with support for ElasticSearch 
7.x and above.

<img src="https://github.com/apache/incubator-ponymail-foal/blob/master/webui/images/foal-demo1.png" style="width: 95%"/>

<img src="https://github.com/apache/incubator-ponymail-foal/blob/master/webui/images/foal-demo2.png" style="width: 95%"/>


## New features in Foal:
Among other things, Foal sports the following new features:

* Improved archiver and import tools
* New, sleeker UI for the end user
* Migration tools for moving to Foal
* 100% Python backend, no Lua required
* In-place editing of emails via web UI

## Installation Guide
Please see the [installation documentation](INSTALL.md) for setup instructions.

### Current setup requirements:

* An operating system, such as:
  * Linux
  * FreeBSD
  * Windows
  * Mac OS
* Python 3.7.3 or higher with dependencies from `requirements.txt` in tools/ and server/ as needed.
* Web server with proxy capabilities for the UI.
* ElasticSearch 7.x or higher.


### Migration disclaimer:
_While compatible with the original Pony Mail, this will not be a drop-in replacement.
Migration of the old database is required, and most of the older ID generators have 
been dropped in favor of collision-secure generators._

### Known Limitations:
* emails are filed according to the Date: header, rather than arrival time.
 This can cause emails to appear in the wrong month or year, or even be future-dated.
* Whilst the underlying database can handle any number of emails in a month,
 the UI and much of the API does not scale well beyond around 10,000 emails per month per list.
* Re-archiving/importing an email that was previously hidden will unhide it in the archive.

#### Known limitations when migrating from older Pony Mail instances:
* If an email is re-imported or re-archived after a migration, the database entry is currently fully replaced.
  This can result in loss of attributes such as alternate Permalinks.
* The migration tool can drop Permalinks if two existing entries point to a sufficiently similar email
* The migration tool does not fix up badly-parsed message-ids etc
* There is no longer a 1-to-1 relationship between mbox and source entries.
  This can result in orphan source entries, with implications for privacy redaction.
* Header parsing is stricter than before; in particular some unusual Message-IDs are not handled correctly.
  This affects use of Foal as a replacement for Apache mod_mbox mail archives.
