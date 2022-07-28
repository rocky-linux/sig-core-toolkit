# This script can be called to do single syncs or full on syncs.

import argparse

from empanadas.common import *
from empanadas.util import Checks
from empanadas.util import RepoSync

# Start up the parser baby
parser = argparse.ArgumentParser(description="Peridot Sync and Compose")

# All of our options
parser.add_argument('--release', type=str, help="Major Release Version or major-type (eg 9-beta)", required=True)
parser.add_argument('--repo', type=str, help="Repository name")
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
parser.add_argument('--refresh-treeinfo', action='store_true')
# I am aware this is confusing, I want podman to be the default option
parser.add_argument('--simple', action='store_false')
parser.add_argument('--logger', type=str)
parser.add_argument('--disable-gpg-check', action='store_false')
parser.add_argument('--disable-repo-gpg-check', action='store_false')

# Parse them
results = parser.parse_args()
rlvars = rldict[results.release]
major = rlvars['major']

r = Checks(rlvars, config['arch'])
r.check_valid_arch()

# Send them and do whatever I guess
a = RepoSync(
        rlvars,
        config,
        major=major,
        repo=results.repo,
        arch=results.arch,
        ignore_debug=results.ignore_debug,
        ignore_source=results.ignore_source,
        repoclosure=results.repoclosure,
        skip_all=results.skip_all,
        hashed=results.hashed,
        parallel=results.simple,
        dryrun=results.dry_run,
        fullrun=results.full_run,
        nofail=results.no_fail,
        logger=results.logger,
        refresh_extra_files=results.refresh_extra_files,
        refresh_treeinfo=results.refresh_treeinfo,
        gpg_check=results.disable_gpg_check,
        repo_gpg_check=results.disable_repo_gpg_check,
)

def run():
    a.run()
