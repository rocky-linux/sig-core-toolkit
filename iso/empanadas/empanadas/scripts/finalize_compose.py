# This script can be called to do single syncs or full on syncs.

import argparse

from empanadas.common import *
from empanadas.util import Checks
from empanadas.util import RepoSync

# Start up the parser baby
parser = argparse.ArgumentParser(description="Peridot Sync and Compose")

# All of our options
parser.add_argument('--release', type=str, help="Major Release Version or major-type (eg 9-beta)", required=True)
parser.add_argument('--arch', type=str, help="Architecture")
parser.add_argument('--logger', type=str)

# Parse them
results = parser.parse_args()
rlvars = rldict[results.release]
major = rlvars['major']

r = Checks(rlvars, config['arch'])
r.check_validity()

# Send them and do whatever I guess
a = RepoSync(
        rlvars,
        config,
        major=major,
        arch=results.arch,
        logger=results.logger,
)

def run():
    a.run_compose_closeout()
