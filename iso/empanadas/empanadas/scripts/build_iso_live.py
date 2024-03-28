# builds ISO's

import argparse

from empanadas.common import *
from empanadas.util import Checks
from empanadas.util import LiveBuild

parser = argparse.ArgumentParser(description="Live ISO Compose")

parser.add_argument('--release', type=str, help="Major Release Version or major-type (eg 9-beta)", required=True)
parser.add_argument('--isolation', type=str, help="Mock Isolation")
parser.add_argument('--local-compose', action='store_true', help="Compose Directory is Here")
parser.add_argument('--peridot', action='store_true', help="Use peridot repos")
parser.add_argument('--image', type=str, help="Granular choice in which live image is built")
parser.add_argument('--logger', type=str)
parser.add_argument('--live-iso-mode', type=str, default='local')
parser.add_argument('--hashed', action='store_true')
parser.add_argument('--just-copy-it', action='store_true', help="Just copy the images to the compose dir")
parser.add_argument('--force-build', action='store_true', help="Just build and overwrite the images")
parser.add_argument('--builder', type=str, help="Choose a builder type and override the set value in the configs")
results = parser.parse_args()
rlvars = rldict[results.release]
major = rlvars['major']

a = LiveBuild(
        rlvars,
        config,
        major=major,
        isolation=results.isolation,
        live_iso_mode=results.live_iso_mode,
        image=results.image,
        compose_dir_is_here=results.local_compose,
        peridot=results.peridot,
        hashed=results.hashed,
        justcopyit=results.just_copy_it,
        force_build=results.force_build,
        builder=results.builder,
        logger=results.logger
)

def run():
    a.run_build_live_iso()
