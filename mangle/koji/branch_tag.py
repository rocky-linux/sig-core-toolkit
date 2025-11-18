#!/usr/bin/env python3
# Build out release tags into koji

import sys
import argparse
import koji

parser = argparse.ArgumentParser(description="Generate tags")
parser.add_argument('--major', type=str, required=True)
parser.add_argument('--minor', type=str, required=True,
                    choices=('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'))
parser.add_argument('--riscv', action='store_true')
parser.add_argument('--modularity', action='store_true')

results = parser.parse_args()
MAJOR = results.major
MINOR = results.minor
RISCV = results.riscv
MODULES = results.modules
RELEASE = f'{MAJOR}.{MINOR}'
PREFIX = f'dist-rocky{RELEASE}'
TOOLS = f'dist-rocky{MAJOR}-build-tools'
MODULE_BUILD = f'module-rocky{RELEASE}-build'
DEFAULT_ARCHES = 'x86_64 aarch64 ppc64le s390x'

# RelEng: Every build tag will have repo.auto. Even though this isn't
# required (as per upstream), we're setting it anyway. Note that all other
# extra options are set at the build-tools tag. This allows us to override
# things like noarch_arches or even mock.new_chroot (e.g. for kiwi).
DEFAULT_EXTRA = {'repo.auto': True}
UPDATES = {'rpm.macro.distcore': f'.el{MAJOR}_{MINOR}'}
RISCV_NOARCH = {'noarch_arches': 'riscv64'}
UPDATES_EXTRA = {**DEFAULT_EXTRA, **UPDATES}
RISCV_EXTRA = {**DEFAULT_EXTRA, **RISCV_NOARCH}
RISCV_UPDATES_EXTRA = {**UPDATES_EXTRA, **RISCV_NOARCH}
KIWI = {**DEFAULT_EXTRA, 'mock.new_chroot': 0}
MODULE_EXTRA = {
        'rpm.macro.distribution': f'Rocky Linux {MAJOR}',
        'rpm.macro.vendor': 'Rocky Enterprise Software Foundation',
}

# RelEng: riscv64 has separate build tags until we have more hardware or
# hardware that can actually build things in a relatively decent amount of
# time. Having separate build tags is important for this in particular.
TARGETS = {
        # Standard build tags
        f'{PREFIX}-build': {
            'build': f'{PREFIX}-build', 'dest': f'{PREFIX}'},
        f'{PREFIX}-updates': {
            'build': f'{PREFIX}-updates-build', 'dest': f'{PREFIX}',
            'extra': UPDATES_EXTRA},
        # Kiwi build tags
        f'{PREFIX}-kiwi': {
            'build': f'{PREFIX}-kiwi', 'dest': f'{PREFIX}',
            'parent': f'{PREFIX}-build',
            'external': [
                {f'sig-core-{MAJOR}-infra': {'pri': 4, 'mode': 'koji'}}
            ],
            'extra': KIWI},
        f'{PREFIX}-kiwi-altarch': {
            'build': f'{PREFIX}-kiwi-altarch', 'dest': f'{PREFIX}',
            'parent': f'{PREFIX}-build',
            'arches': 'aarch64',
            'external': [
                {f'sig-core-{MAJOR}-infra': {'pri': 4, 'mode': 'koji'}},
                {f'sig-altarch-{MAJOR}-common': {'pri': 7, 'mode': 'koji'}},
                {f'sig-altarch-{MAJOR}-rockyrpi': {'pri': 8, 'mode': 'koji'}}
            ],
            'extra': KIWI},

        # Only very specific images need epel and cloud-common
        f'{PREFIX}-kiwi-cloud-epel': {
            'build': f'{PREFIX}-kiwi-cloud-epel', 'dest': f'{PREFIX}',
            'parent': f'{PREFIX}-build',
            'arches': 'x86_64 aarch64',
            'external': [
                {f'sig-core-{MAJOR}-infra': {'pri': 4, 'mode': 'bare'}},
                {f'sig-cloud-{MAJOR}-common': {'pri': 5, 'mode': 'bare'}},
                {f'epel-{MAJOR}-stable': {'pri': 6, 'mode': 'bare'}}
            ],
            'extra': KIWI},
        f'{PREFIX}-kiwi-epel': {
            'build': f'{PREFIX}-kiwi-epel', 'dest': f'{PREFIX}',
            'parent': f'{PREFIX}-build',
            'external': [
                {f'sig-core-{MAJOR}-infra': {'pri': 4, 'mode': 'bare'}},
                {f'epel-{MAJOR}-stable': {'pri': 6, 'mode': 'bare'}}
            ],
            'extra': KIWI},

        # Some builds need nspawn on, so this facilitates it
        f'{PREFIX}-kiwi-nspawn': {
            'parent': f'{PREFIX}-build',
            'build': f'{PREFIX}-kiwi-nspawn', 'dest': f'{PREFIX}',
            'external': [
                {f'sig-core-{MAJOR}-infra': {'pri': 4, 'mode': 'koji'}}
            ],
        },
}

RISCV_TARGETS = {
        f'{PREFIX}-build-riscv64': {
            'build': f'{PREFIX}-build-riscv64', 'dest': f'{PREFIX}',
            'extra': RISCV_EXTRA,
            'arches': 'riscv64'},
        f'{PREFIX}-updates-riscv64': {
            'build': f'{PREFIX}-updates-build-riscv64', 'dest': f'{PREFIX}',
            'extra': RISCV_UPDATES_EXTRA,
            'arches': 'riscv64'},
}

if RISCV:
    TARGETS.update(RISCV_TARGETS)

session = koji.ClientSession('https://kojidev.rockylinux.org/kojihub')
try:
    session.gssapi_login()
except koji.GSSAPIAuthError as exc:
    print(f"Please verify your kerberos credentials: {exc}")
    sys.exit(1)

build_tools_id = session.getTag(TOOLS)['id']
build_tools_inh = {
        'parent_id': build_tools_id,
        'priority': 1,
        'maxdepth': None,
        'intransitive': False,
        'noconfig': False,
        'pkg_filter': ''
}

for target, info in TARGETS.items():
    build = info.get('build')
    dest = info.get('dest')
    parent = info.get('parent', dest)
    arches = info.get('arches', DEFAULT_ARCHES)
    externals = info.get('external', [])
    extras = info.get('extra', DEFAULT_EXTRA)

    try:
        # Make tags with parents and data
        session.createTag(
                build,
                parent=parent,
                arches=arches,
                extra=extras
        )
        # Add inheritance for the tools tag
        session.setInheritanceData(
                build,
                data=[build_tools_inh]
        )

        # setup externals - usually only kiwi tags should have these.
        for external in externals:
            for repo_name, repo_info in external.items():
                pri = repo_info.get('pri')
                mode = repo_info.get('mode', 'koji')
                extarches = repo_info.get('arches', None)
                session.addExternalRepoToTag(
                        build,
                        repo_name,
                        pri,
                        merge_mode=mode,
                        arches=extarches
                )

        # Setup target
        session.createBuildTarget(
                target,
                build,
                dest
        )

    except koji.GenericError as exc:
        print(exc)
        print('There was an error; exiting to prevent further problems')
        sys.exit(1)

try:
    print('!! Creating compose tag')
    session.createTag(f'{PREFIX}-compose', parent=PREFIX)

    if MODULES:
        print('!! Creating module build tag')
        session.createTag(f'{MODULE_BUILD}', arches=DEFAULT_ARCHES, extra=MODULE_EXTRA)

except koji.GenericError as exc:
    print(exc)
    print('There was an error; exiting to prevent further problems')
    sys.exit(1)
