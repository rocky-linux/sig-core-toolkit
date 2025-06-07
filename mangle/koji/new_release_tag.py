#!/usr/bin/env python3
# Build out release tags into koji

import sys
import argparse
import koji

parser = argparse.ArgumentParser(description="Generate tags")
parser.add_argument('--major', type=str, required=True)

results = parser.parse_args()
MAJOR = results.major
PREFIX = f'dist-rocky{MAJOR}'
TOOLS = f'dist-rocky{MAJOR}-build-tools'
DEFAULT_ARCHES = 'x86_64 aarch64 ppc64le s390x'
SECOND_ARCHES = 'riscv64'

# RelEng: Every build tag will have repo.auto. Even though this isn't
# required (as per upstream), we're setting it anyway. Note that all other
# extra options are set at the build-tools tag. This allows us to override
# things like noarch_arches or even mock.new_chroot (e.g. for kiwi).
DEFAULT_EXTRA = {'repo.auto': True}
RISCV = {'noarch_arches': 'riscv64'}
RISCV_EXTRA = {**DEFAULT_EXTRA, **RISCV}
KIWI = {**DEFAULT_EXTRA, 'mock.new_chroot': 0}

# RelEng: riscv64 has separate build tags until we have more hardware or
# hardware that can actually build things in a relatively decent amount of
# time. Please keep them separate for now.
TARGETS = {}

session = koji.ClientSession('https://kojidev.rockylinux.org/kojihub')
try:
    session.gssapi_login()
except koji.GSSAPIAuthError as exc:
    print(f"Please verify your kerberos credentials: {exc}")
    sys.exit(1)

# Create initial tags
# Create all inheritance
# Setup build tags after (initial and lookahead)

build_tools_id = session.getTag(TOOLS)['id']
build_tools_inh = {
        'parent_id': build_tools_id,
        'priority': 1,
        'maxdepth': None,
        'intransitive': False,
        'noconfig': False,
        'pkg_filter': ''
}
