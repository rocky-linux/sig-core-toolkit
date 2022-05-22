# iso

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

* Callable scripts should *not* end in `.py`
* They should have at least `775` or `+x` permissions
