# This is for doing repoclosures upstream

import argparse

from empanadas.common import *
from empanadas.util import Checks
from empanadas.util import RepoSync

# Start up the parser baby
parser = argparse.ArgumentParser(description="Peridot Upstream Repoclosure")

# All of our options
parser.add_argument('--release', type=str, help="Major Release Version or major-type (eg 9-beta)", required=True)
parser.add_argument('--simple', action='store_false')
parser.add_argument('--enable-repo-gpg-check', action='store_true')
parser.add_argument('--logger', type=str)

# Parse them
results = parser.parse_args()
rlvars = rldict[results.release]
major = rlvars['major']

r = Checks(rlvars, config['arch'])
r.check_valid_arch()

a = RepoSync(
        rlvars,
        config,
        major=major,
        parallel=results.simple,
        repo_gpg_check=results.enable_repo_gpg_check,
        logger=results.logger,
)

def run():
    a.run_upstream_repoclosure()
