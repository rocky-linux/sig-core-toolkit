# This script can be called to do single syncs or full on syncs.

import argparse
from empanadas.common import *
from empanadas.util import Checks
from empanadas.util import SigRepoSync

#rlvars = rldict['9']
#r = Checks(rlvars, config['arch'])
#r.check_valid_arch()

# Start up the parser baby
parser = argparse.ArgumentParser(description="Peridot Sync and Compose")

# All of our options
parser.add_argument('--release', type=str, help="Major Release Version", required=True)
parser.add_argument('--repo', type=str, help="Repository name")
parser.add_argument('--sig', type=str, help="SIG name", required=True)
parser.add_argument('--arch', type=str, help="Architecture")
parser.add_argument('--ignore-debug', action='store_true')
parser.add_argument('--ignore-source', action='store_true')
parser.add_argument('--repoclosure', action='store_true')
parser.add_argument('--skip-all', action='store_true')
parser.add_argument('--hashed', action='store_true')
parser.add_argument('--dry-run', action='store_true')
parser.add_argument('--full-run', action='store_true')
parser.add_argument('--no-fail', action='store_true')
parser.add_argument('--refresh-extra-files', action='store_true')
# I am aware this is confusing, I want podman to be the default option
parser.add_argument('--simple', action='store_false')
parser.add_argument('--logger', type=str)

# Parse them
results = parser.parse_args()

rlvars = rldict[results.release]
sigvars = sigdict[results.sig][results.release]
r = Checks(rlvars, config['arch'])
r.check_valid_arch()

# Send them and do whatever I guess
a = SigRepoSync(
        rlvars,
        config,
        sigvars,
        major=results.release,
        repo=results.repo,
        arch=results.arch,
        ignore_source=results.ignore_source,
        ignore_debug=results.ignore_debug,
        repoclosure=results.repoclosure,
        skip_all=results.skip_all,
        hashed=results.hashed,
        parallel=results.simple,
        dryrun=results.dry_run,
        fullrun=results.full_run,
        nofail=results.no_fail,
        logger=results.logger
)


def run():
    a.run()
