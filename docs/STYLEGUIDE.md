# Development style guide

__This document is a work in progress. More to come later, feedback and suggestions are most welcome.__
## ECMAScript Standards
- Foal uses ECMAScript 9th edition (2018) as the base scripting language for the browser interface.
- All global variables must be declared with `G_` prepended, such as: `G_apiURL` or `G_current_json`

## Python Standards
- Foal requires Python 3.7 or above, following the PEP8 specifications with a 120 character maximum per line.
  - Automatic linting of new code can be done using [Black](https://github.com/psf/black/): `black -l 120 foo.py`
- All code should be typed and is checked with [mypy](https://github.com/python/mypy/)
