#!/usr/bin/env python3
# label <label@rockylinux.org>
import datetime
import sys
import dnf
import dnf.exceptions

# pylint: disable=unnecessary-lambda-assignment
now = datetime.datetime.today().strftime("%m-%d-%Y %T")

class DnfQuiet(dnf.Base):
    """
    DNF object

    This is in the event we need special functions
    """
    def __init__(self):
        dnf.Base.__init__(self)

def main():
    """
    Main run
    """
    dnfobj = DnfQuiet()
    releasever = dnfobj.conf.releasever
    try:
        dnfobj.read_all_repos()
    # pylint: disable=bare-except
    except:
        print(f'[-] {now} -> Could not read repos', file=sys.stderr)
        sys.exit(1)

    rocky_default_repos = {
            '8': ['baseos', 'appstream', 'extras'],
            '9': ['baseos', 'appstream', 'extras']
    }.get(releasever, None)

    if not rocky_default_repos:
        print(f'[-] {now} -> Not a Rocky Linux system')
        sys.exit(1)

    print(f'[-] {now} -> Checking if non-default repo is enabled')
    _not_allowed=False
    for repo in list(dnfobj.repos.iter_enabled()):
        if not repo.id in rocky_default_repos:
            print(f'[-] {now} -> {repo.id} is enabled and should be disabled')
            _not_allowed=True
    if _not_allowed:
        print(f'[-] {now} -> FAIL - There are extra repos enabled')
        sys.exit(1)

    print(f'[-] {now} -> PASS')
    sys.exit(0)

if __name__ == "__main__":
    main()
