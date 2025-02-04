# Use this to test upcoming functionality

import argparse
import sys

from empanadas.common import *
from empanadas.util import Checks

# Start up the parser baby
parser = argparse.ArgumentParser(description="Peridot Upstream Repoclosure")

# All of our options
parser.add_argument('--release', type=str, help="Major Release Version or major-type (eg 9-beta)", required=True)

# Parse them
results = parser.parse_args()
rlvars = rldict[results.release]
major = rlvars['major']

r = Checks(rlvars, config['arch'])
r.check_validity()

def run():
    print(sys.path)
