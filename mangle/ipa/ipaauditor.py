#!/usr/bin/env python3
# -*-:python; coding:utf-8; -*-
# author: Louis Abel <label@rockylinux.org>
#
# This script acts as a auditor for a FreeIPA domain. By default, it will
# communicate with an IPA server of a domain, login, and attempt to get all
# information for HBAC and SUDO.

import sys

python_freeipa = True
ipalib = True

try:
    from python_freeipa import ClientMeta
except ImportError:
    python_freeipa = None

try:
    from ipalib import api
except ImportError:
    ipalib = None

if not ipalib and not python_freeipa:
    print('No IPA python modules are available')
    sys.exit(1)
