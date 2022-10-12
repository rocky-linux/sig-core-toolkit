#!/usr/bin/python3
import os
import os.path
import json
import dnf

# Init the dnf configuration
base = dnf.Base()
conf = base.conf
base.read_all_repos()
all_repos = base.repos.all()
all_repos.disable()
base.repos.add_new_repo('all-source', conf, baseurl=['https://yumrepofs.build.resf.org/v1/projects/55b17281-bc54-4929-8aca-a8a11d628738/repo/all/src'])
base.fill_sack()

q = base.sack.query()
a = q.available()
pkg_list = []

for packages in a:
    nevr = '{}-{}:{}-{}'.format(
            packages.name,
            packages.epoch,
            packages.version,
            packages.release
    )
    pkg_list.append(nevr)

pkg_list.sort()
print(pkg_list)
