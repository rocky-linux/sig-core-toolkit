# This script can be called to do single syncs or full on syncs.

import argparse
from empanadas.common import *
from empanadas.util import Checks
from empanadas.util import SigRepoSync

#rlvars = rldict['9']
#r = Checks(rlvars, config['arch'])
#r.check_validity()

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
parser.add_argument('--log-level', type=str, default='INFO')
parser.add_argument('--disable-gpg-check', action='store_false')
parser.add_argument('--disable-repo-gpg-check', action='store_false')
parser.add_argument('--clean-old-packages', action='store_true')

# Parse them
results = parser.parse_args()

rlvars = rldict[results.release]
sigvars = sigdict[results.sig][results.release]
r = Checks(rlvars, config['arch'])
r.check_validity()

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
        refresh_extra_files=results.refresh_extra_files,
        logger=results.logger,
        log_level=results.log_level,
        gpg_check=results.disable_gpg_check,
        repo_gpg_check=results.disable_repo_gpg_check,
        reposync_clean_old=results.clean_old_packages,
)


def run():
    a.run()
