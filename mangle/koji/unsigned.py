#!/usr/bin/env python3
# Checks for unsigned packages in a given tag and key name
# label <label@resf.org>
import sys
import argparse
import koji
builds = []
binfos = []
rpmdict = {}
unsigned = []
errors = {}

STATUS = 0
HUB = 'https://kojidev.rockylinux.org/kojihub'

# Place all known keys here. IMA signing does not matter. What matters is that
# they are signed with the given key ID.
KEYS = {
        'rocky-linux-8': {'id': '6d745a60'},
        'rocky-linux-10': {'id': '6fedfc85'}
}

parser = argparse.ArgumentParser(description="Koji Signing Check")
parser.add_argument('--key', type=str, help="Signing key name", required=True)
parser.add_argument('--tag', type=str, help="Tag", required=True)
parsed = parser.parse_args()

key = parsed.key
tag = parsed.tag

if not key in KEYS:
    print(f'Unknown key {key}')
    sys.exit(1)

kojisession = koji.ClientSession(HUB)
builds = [build['nvr'] for build in
            kojisession.listTagged(tag, latest=True, inherit=True)]

builds = sorted(builds)

kojisession.multicall = True
for build in builds:
    kojisession.getBuild(build, strict=True)

for build, result in zip(builds, kojisession.multiCall()):
    if isinstance(result, list):
        binfos.append(result)
    else:
        errors.setdefault('Builds', []).append(build)
        STATUS += 1

kojisession.multicall = True
for [binfo] in binfos:
    kojisession.listRPMs(buildID=binfo['id'])

results = kojisession.multiCall()
for [rpms] in results:
    for rpm in rpms:
        rpmdict[f"{rpm['nvr']}.{rpm['arch']}"] = rpm['id']

# Get unsigned packages
kojisession.multicall = True
for rpm in rpmdict.keys():
    kojisession.queryRPMSigs(rpm_id=rpmdict[rpm], sigkey=KEYS[key]['id'])

results = kojisession.multiCall()
for ([result], rpm) in zip(results, rpmdict.keys()):
    if not result:
        unsigned.append(rpm)

print('\n'.join(unsigned))
