# iso

## Setup / Install

1. Install [Poetry](https://python-poetry.org/docs/)
2. Setup: `poetry install`
3. Install dependencies: `dnf install podman mock`
4. Have fun

Deeper documenation can be found at the [SIG/Core Wiki](https://sig-core.rocky.page/documentation).

## Reliance on podman and mock

### Why podman?

Podman is a requirement for performing reposyncs. This was done because it was found to be easier to spin up several podman containers than several mock chroots and it was faster than doing one at a time in a loop. Podman is also used to parallelize ISO builds.

### Why mock?

There are cases where running `mock` is the preferred go-to: For example, building lorax images. Since you cannot build a lorax image for an architecture your system does not support, trying to "parallelize" it was out of the question. Adding this support in was not only for local testing without podman, it was also done so it can be run in our peridot kube cluster for each architecture.

## Updating dependencies

Dependencies can be manipulated via the pyproject.toml file or with the poetry add/remove commands.

Changes to the poetry.lock should be commited if dependencies are added or updated.

## TODO

* Verbose mode should exist to output everything that's being called or ran.
* There should be additional logging regardless, not just to stdout, but also to a file.

## scripts

```
* sync_from_peridot    -> Syncs repositories from Peridot
* sync_sig             -> Syncs SIG repositories from Peridot
* build-iso            -> Builds initial ISO's using Lorax
* build-iso-extra      -> Builds DVD's and other images based on Lorax data
* build-iso-live       -> Builds live images
* pull-unpack-tree     -> Pulls the latest lorax data from an S3 bucket and configures treeinfo
* pull-cloud-image     -> Pulls the latest cloud images from an S3 bucket
* finalize_compose     -> Finalizes a compose with metadata and checksums, as well as copies images
* launch-builds        -> Creates a kube config to run build-iso
* build-image          -> Runs build-iso
* generate_compose     -> Creates a compose directory right away and optionally links it as latest
                          (You should only use this if you are running into errors with images)
* peridot_repoclosure  -> Runs repoclosure against a peridot instance
```

## wrappers

```
* common               -> The starting point
* iso_utils            -> Does work for ISO building and generation
* dnf_utils            -> Does work for repo building and generation
* check                -> Checks if the architecture/release combination are valid
* shared               -> Shared utilities between all wrappers
```

## rules

### imports

When making a script, you *must* import common. This is insanely bad practice,
but we would prefer if we started out this way:

```
import argparse
from empanadas.common import *
from empanadas.util import Checks
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
r.check_validity()
```

### script names and permissions

* Callable scripts should always end in `.py` and live in the empanadas/scripts folder
* Poetry will handle the installation of these executables with setuptools for distribution, and they can be invoked by name using `poetry run script-name`, too.
  * Configure the script and function to be executed in pyproject.toml (TODO: dynamically load scripts from this directory as well as standardize on the script input/outputs)
