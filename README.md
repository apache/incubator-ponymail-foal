# Apache Pony Mail Foal
_Next generation suite of services and tools for Apache Pony Mail_

![CI Status](https://img.shields.io/travis/apache/incubator-ponymail-foal?style=plastic)

This repository aims to contain the next generation of Apache Pony Mail,
a pure python version of Apache Pony Mail with support for ElasticSearch 6.x and above.


### Roadmap
Work is underway on the following items:

- Improved archiver and import tools   **[DONE]**
- New UI for the end user              **[DONE]**
- 100% python backend, no mod_lua required. **[COMING SOON]**


### Migration disclaimer:
_While compatible with the original Pony Mail, this will not be a drop-in replacement.
Migration of the old database will be needed, and there may be edge cases where 
re-imaging a database from scratch (re-importing from mbox files as opposed to migrating 
your ElasticSearch database) will not produce the exact same permalinks as before, if 
the input options don't match exactly. For lists with a List-ID header present in all 
emails (and no override used), this should not be the case for any permalinks, and 
they should be the same. If you have an existing Pony Mail database, migrating it 
with the provided migration tool is highly recommended if you wish to preserve old 
permalinks._
