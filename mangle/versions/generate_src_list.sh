#!/bin/bash

OLD_REPO="https://yumrepofs.build.resf.org/v1/projects/dff20351-7d36-4f7c-9eea-7f039f5026d0/repo/all/src"
NEW_REPO="https://yumrepofs.build.resf.org/v1/projects/6202c09e-6252-4d3a-bcd3-9c7751682970/repo/all/src"

dnf repoquery --repofrompath=p,${OLD_REPO} --disablerepo=* --enablerepo=p -q -a --qf '%{NAME}-%{EPOCH}:%{VERSION}-%{RELEASE}' > /tmp/list_a

dnf repoquery --repofrompath=q,${NEW_REPO} --disablerepo=* --enablerepo=q -q -a --qf '%{NAME}-%{EPOCH}:%{VERSION}-%{RELEASE}' > /tmp/list_b

echo "Please manually compare to check for brand new or obsoleted packages"
