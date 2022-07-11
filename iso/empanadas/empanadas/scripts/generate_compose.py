# This script can be called to do single syncs or full on syncs.

import argparse
import logging
import sys

from empanadas.common import *
from empanadas.util import Checks
from empanadas.util import RepoSync
from empanadas.util import Shared

# Start up the parser baby
parser = argparse.ArgumentParser(description="Peridot Sync and Compose")

# All of our options
parser.add_argument('--release', type=str, help="Major Release Version or major-type (eg 9-beta)", required=True)
parser.add_argument('--logger', type=str)

# Parse them
results = parser.parse_args()
rlvars = rldict[results.release]
major = rlvars['major']

r = Checks(rlvars, config['arch'])
r.check_valid_arch()

# Send them and do whatever I guess
def run():
    if results.logger is None:
        log = logging.getLogger("generate")
        log.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s :: %(name)s :: %(message)s',
            '%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        log.addHandler(handler)
    else:
        log = results.logger

    compose_base = config['compose_root'] + "/" + major
    shortname = config['shortname']
    version = rlvars['revision']
    date_stamp = config['date_stamp']
    profile = rlvars['profile']
    logger = log

    generated_dir = Shared.generate_compose_dirs(
            compose_base,
            shortname,
            version,
            date_stamp,
            logger
    )

    if results.symlink:
        compose_latest_dir = os.path.join(
                config['compose_root'],
                major,
                "latest-{}-{}".format(
                    shortname,
                    profile,
                )
        )
        if os.path.exists(compose_latest_dir):
            os.remove(compose_latest_dir)

        os.symlink(generated_dir, compose_latest_dir)

    log.info('Generated compose dirs.')
