# This is a testing script to ensure the RepoSync class is working as intended.

import argparse

from empanadas.common import *
from empanadas.util import Checks
from empanadas.util import RepoSync

rlvars = rldict['9-lookahead']
r = Checks(rlvars, config['arch'])
r.check_valid_arch()

#a = RepoSync(rlvars, config, major="9", repo="ResilientStorage", parallel=True, ignore_debug=False, ignore_source=False)
a = RepoSync(rlvars, config, major="9", repo="BaseOS", parallel=True, ignore_debug=False, ignore_source=False, hashed=True)
<<<<<<< HEAD:iso/py/sync-from-peridot-test
#a.run()
=======

def run():
    a.run()
>>>>>>> 8d29760 (Lets write some poetry):iso/empanadas/empanadas/scripts/sync-from-peridot-test.py
