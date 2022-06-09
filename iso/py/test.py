#!/usr/bin/env python3

from common import *
import argparse
from util import Checks

rlvars = rldict['9']
r = Checks(rlvars, arch)
r.check_valid_arch()
