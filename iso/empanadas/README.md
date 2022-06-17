# iso


## Setup / Install

1. Install [Poetry](https://python-poetry.org/docs/)
2. Setup: `poetry install`
3. Have fun


## Updating dependencies

Dependencies can be manipulated via the pyproject.toml file or with the poetry add/remove commands.

Changes to the poetry.lock should be commited if dependencies are added or updated.

## TODO

Verbose mode should exist to output everything that's being called or ran.

There should be additional logging regardless, not just to stdout, but also to a file.

## scripts

* sync-variant-pungi
* sync-variant-peridot
* sync-from-pungi
* sync-from-peridot
* sync-sig
* build-all-iso
* sign-repos-only

## wrappers

* lorax-generators
* sync-generators

## rules

### imports

When making a script, you *must* import common. This is insanely bad practice,
but we would prefer if we started out this way:

```
from common import *
import argparse
```

Whatever is imported in common will effectively be imported in your scripts as
well, but there is nothing stopping you from defining them again, even out of
habit. `argparse` is there because you better have a very, *very* good reason
to not be writing scripts that are major version specific.

If you are writing something that could be arch specific based on the major
version (which is likely), make sure to import the util module and use it arch
checker appropriately. Small (but weak) example.

```
from util import Checks

rlvars = rldict['9']
r = Checks(rlvars, arch)
r.check_valid_arch()
```

### script names and permissions

* Callable scripts should always end in `.py` and live in the empanadas/scripts folder
* Poetry will handle the installation of these executables with setuptools for distribution, and they can be invoked by name using `poetry run script-name`, too.
  * Configure the script and function to be executed in pyproject.toml (TODO: dynamically load scripts from this directory as well as standardize on the script input/outputs)
