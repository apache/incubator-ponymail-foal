# Apache Pony Mail Foal
<img src="https://github.com/apache/incubator-ponymail-foal/blob/master/webui/images/foal.png" width="72" align="left"/>

_Next generation suite of services and tools for Apache Pony Mail_

![CI Status](https://img.shields.io/travis/apache/incubator-ponymail-foal?style=plastic)

This repository aims to contain the next generation of Apache Pony Mail,
a pure python version of Apache Pony Mail with support for ElasticSearch 
7.x and above.


## New features in Foal:
Among other things, Foal sports the following new features:

- Improved archiver and import tools
- New, sleeker UI for the end user
- Migration tools for moving to Foal
- 100% python backend, no Lua required
- In-place editing of emails via web UI

## Installation Guide
Please see the [installation documentation](INSTALL.md) for setup instructions.

### Current setup requirements:

- An operating system, such as:
- - Linux
- - FreeBSD
- - Windows
- - Mac OS
- Python 3.7.3 or higher with dependencies from `requirements.txt`.
- Web server with proxy capabilities for the UI.
- ElasticSearch 7.x or higher.


### Migration disclaimer:
_While compatible with the original Pony Mail, this will not be a drop-in replacement.
Migration of the old database is required, and most of the older ID generators have 
been dropped in favor of collision-secure generators._
