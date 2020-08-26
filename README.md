# Apache Pony Mail Foal
_Next generation suite of services and tools for Apache Pony Mail_

![CI Status](https://img.shields.io/travis/apache/incubator-ponymail-foal?style=plastic)

This repository aims to contain the next generation of Apache Pony Mail,
a pure python version of Apache Pony Mail with support for ElasticSearch 6.x and above.


## Roadmap
Work is underway on the following items:

- Improved archiver and import tools   **[DONE]**
- New UI for the end user              **[DONE]**
- 100% python backend, no mod_lua required. **[COMING SOON]**

## Installation Guide
Work is under way to write an installation guide for this.
As several components are not finished or in working order yet, this is pending.

### Current setup requirements:

- Linux or other UNIX based operating system (Windows has not been tested, but might work).
- Python 3.8 or higher with dependencies from `requirements.txt`.
- Web server with proxy capabilities for the UI.
- ElasticSearch 6.x or higher, 7.x recommended.


### Migration disclaimer:
_While compatible with the original Pony Mail, this will not be a drop-in replacement.
Migration of the old database will be needed, and there will be cases where 
re-imaging a database from scratch (re-importing from mbox files as opposed to migrating 
your ElasticSearch database) will not produce the exact same permalinks as before, if 
the input options don't match exactly. For lists with a List-ID header present in all 
emails (and no override used), this should not be the case for any permalinks, and 
they should be the same. If you have an existing Pony Mail database, migrating it 
with the provided migration tool is highly recommended if you wish to preserve old 
permalinks._
