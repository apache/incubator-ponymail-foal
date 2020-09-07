# Apache Pony Mail Foal
_Next generation suite of services and tools for Apache Pony Mail_

![CI Status](https://img.shields.io/travis/apache/incubator-ponymail-foal?style=plastic)

This repository aims to contain the next generation of Apache Pony Mail,
a pure python version of Apache Pony Mail with support for ElasticSearch 6.x and above.


## Roadmap
Work is underway on the following items:

- Improved archiver and import tools   **[DONE]**
- New UI for the end user              **[DONE]**
- 100% python backend, no mod_lua required. **[IN PROGRESS]**

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
Migration of the old database is required, and several older ID generators have been
dropped in favor of collision-secure generators._
