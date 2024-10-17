#!/usr/bin/env python3
import os
import os.path
import json
import argparse
import dnf
import createrepo_c as cr
from common import *

parser = argparse.ArgumentParser(description="Version Parser")
parser.add_argument('--version', type=str, required=True)
parser.add_argument('--stream', action='store_true', help="Stream koji only")
parser.add_argument('--all-repo', action='store_true', help="Looks at the all repo for peridot")
results = parser.parse_args()

REPOS = switcher.rlver(results.version,
                       stream=results.stream,
                       all_repo=results.all_repo)

# Source packages we do not ship or are rocky branded
IGNORES = [
        'insights-client',
        'shim',
        'shim-unsigned-x64',
        'shim-unsigned-aarch64',
        'redhat-cloud-client-configuration',
        'rhc',
        'rhc-worker-playbook',
        'centos-indexhtml',
        'centos-logos',
        'centos-stream-release',
        'redhat-indexhtml',
        'redhat-logos',
        'redhat-release',
        'openssl-fips-provider'
]

def warningcb(warning_type, message):
    print("WARNING: %s" % message)
    return True

repo_prepop = {}
with open('/tmp/versions.list', 'w+') as fp:
    for k in REPOS:
        repo_prepop[k] = {}
        for arch in REPOS[k]:
            PRIMARY_XML_PATH   = None
            FILELISTS_XML_PATH = None
            OTHER_XML_PATH     = None
            REPO_PATH          = k + '/' + arch
            repomd = cr.Repomd()
            cr.xml_parse_repomd(os.path.join(REPO_PATH, "repodata/repomd.xml"), repomd, warningcb)
            for record in repomd.records:
                if record.type == "primary":
                    PRIMARY_XML_PATH = os.path.join(REPO_PATH, record.location_href)
                elif record.type == "filelists":
                    FILELISTS_XML_PATH = os.path.join(REPO_PATH, record.location_href)
                elif record.type == "other":
                    OTHER_XML_PATH = os.path.join(REPO_PATH, record.location_href)

            package_iterator = cr.PackageIterator(primary_path=PRIMARY_XML_PATH, filelists_path=FILELISTS_XML_PATH, other_path=OTHER_XML_PATH, warningcb=warningcb)
            repo_prepop[k][arch] = {}
            for pkg in package_iterator:
                subject = dnf.subject.Subject(pkg.rpm_sourcerpm)
                possible_nevra = subject.get_nevra_possibilities()
                srcname = possible_nevra[0].name
                srcvers = possible_nevra[0].version
                srcrele = possible_nevra[0].release
                full = srcname + '-' + srcvers + '-' + srcrele
                # Ignore packages (by source) that we do not ship
                if srcname in IGNORES:
                    continue

                # Create the initial list if the package (by source) does not exist
                if srcname not in repo_prepop[k][arch]:
                    repo_prepop[k][arch][srcname] = {}

                # Avoids duplicate entries - This is especially helpful for modules
                repo_prepop[k][arch][srcname]['version'] = srcvers
                repo_prepop[k][arch][srcname]['release'] = srcrele

                fp.write(full + '\n')
    fp.close()

entry_point = open('/tmp/versions.json', 'w+')
json.dump(repo_prepop, entry_point, indent=2, sort_keys=True)
entry_point.close()
