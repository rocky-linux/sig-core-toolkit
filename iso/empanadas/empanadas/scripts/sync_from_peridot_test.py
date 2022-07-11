# This is a testing script to ensure the RepoSync class is working as intended.

import argparse

import empanadas
from empanadas.common import *
from empanadas.util import Checks
from empanadas.util import RepoSync

rlvars = rldict['9-lookahead']
r = Checks(rlvars, config['arch'])
r.check_valid_arch()

#a = RepoSync(rlvars, config, major="9", repo="ResilientStorage", parallel=True, ignore_debug=False, ignore_source=False)
a = RepoSync(rlvars, config, major="9", repo="BaseOS", parallel=True, ignore_debug=False, ignore_source=False, hashed=True)

def run():
    print(rlvars.keys())
    print(rlvars)
    print(empanadas.__version__)
    print(a.hashed)
