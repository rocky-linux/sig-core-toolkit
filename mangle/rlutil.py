#!/usr/bin/env python3
# This helps manage repo files and other little bits of Rocky Linux repos. Use
# at your own risk.
#
# WARNING: USING A RELEASE OLDER THAN THE CURRENT RELEASE IS NOT SUPPORTED.
# PLEASE SEE THE WIKI FOR MORE INFORMATION ON THE CURRENT RELEASES.
# https://wiki.rockylinux.org/rocky/version/
import os
import sys
import re
import argparse
import rpm

dist = rpm.expandMacro("%rocky")
regex = fr'^{dist}\.\d+$'

parser = argparse.ArgumentParser(description='Rocky Linux Repo Utility')
subparser = parser.add_subparsers(dest='cmd')
subparser.required = True
release_parser = subparser.add_parser('release', epilog='Use this to make general changes to the Rocky Linux release dnf repo configuration.')

release_parser.add_argument('--use-baseurl', action='store_true')
release_parser.add_argument('--use-mirrorlist', action='store_true')
release_parser.add_argument('--reset', action='store_true',
                            help='If this script was used to modify the config, this will reset everything back to the defaults.')
release_parser.add_argument('--contentdir',
                            choices=('pub', 'staging', 'stg', 'vault'))
release_parser.add_argument('--switch-to-vault', action='store_true', help='Switches to using the vault.')
release_parser.add_argument('--releasever', type=str, default='', help='Chooses a specific release. USE WITH CAUTION.')

results = parser.parse_args()
command = parser.parse_args().cmd

def all_rocky_files(
        directory_path = '/etc/yum.repos.d',
        filter_filename = lambda file: 'rocky' in file) -> list:
    """
    Filter out specified files
    """
    return_list = []
    for file in os.scandir(directory_path):
        if filter_filename(file.name):
            return_list.append(os.path.join(directory_path, file.name))
    return return_list

def switch_to_baseurl():
    """
    Uncomments baseurl, removes mirrorlist
    """
    repo_files = all_rocky_files()
    print('Switching all rocky repo files to use baseurl')
    for file in repo_files:
        with open(file, "r") as f:
            lines = f.readlines()
        with open(file, "w") as f:
            for line in lines:
                ml_match = re.search(r'^mirrorlist', line)
                bu_match = re.search(r'^#baseurl', line)
                if ml_match:
                    f.write(re.sub(r'^mirrorlist', '#mirrorlist', line))
                elif bu_match:
                    f.write(re.sub(r'^#baseurl', 'baseurl', line))
                else:
                    f.write(line)
            f.close()

def switch_to_mirrorlist():
    """
    Uncomments mirrorlist, removes baseurl
    """
    repo_files = all_rocky_files()
    print('Switching all rocky repo files to use mirror list')
    for file in repo_files:
        with open(file, "r") as f:
            lines = f.readlines()
        with open(file, "w") as f:
            for line in lines:
                ml_match = re.search(r'^#mirrorlist', line)
                bu_match = re.search(r'^baseurl', line)
                if ml_match:
                    f.write(re.sub(r'^#mirrorlist', 'mirrorlist', line))
                elif bu_match:
                    f.write(re.sub(r'^baseurl', '#baseurl', line))
                else:
                    f.write(line)
            f.close()

def set_releasever(releasever):
    """
    Sets a release version
    """
    print(f'Setting releasever to {releasever}')
    with open('/etc/dnf/vars/releasever', 'w') as f:
        f.write(releasever)
        f.close()

def set_contentdir(contentdir):
    """
    Sets the contentdir path to whatever/rocky
    """
    print(f'Setting contentdir to {contentdir}/rocky')
    with open('/etc/dnf/vars/contentdir', 'w') as f:
        f.write(f'{contentdir}/rocky')
        f.close()

def switch_to_vault(releasever):
    """
    Switch to vault
    """
    print('** Switching to use the vault')
    switch_to_baseurl()
    set_contentdir('vault')
    set_releasever(releasever)

def full_reset():
    """
    Resets everything to normal ONLY if this script was used to make changes.
    """
    print('** Resetting mirrorlist')
    switch_to_mirrorlist()
    print('** Resetting contentdir')
    set_contentdir('pub')
    print('** Removing releasever var')
    if os.path.exists('/etc/dnf/vars/releasever'):
        os.remove('/etc/dnf/vars/releasever')

def repoutil(results):
    if results.switch_to_vault:
        if len(results.releasever) == 0 or not re.search(regex, results.releasever):
            print(f'A release version was NOT specified nor correct for this release: {results.releasever}')
            sys.exit(1)
        elif re.search(regex, results.releasever):
            switch_to_vault(results.releasever)
            sys.exit(0)
    elif results.reset:
        full_reset()
    else:
        if results.use_baseurl and results.use_mirrorlist:
            print('You cannot set both baseurl and mirrorlist.')
            sys.exit(1)
    
        if results.use_baseurl:
            switch_to_baseurl()
        elif results.use_mirrorlist:
            switch_to_mirrorlist()
    
        if len(results.releasever) > 0:
            set_releasever(results.releasever)

        if results.contentdir:
            set_contentdir(results.contentdir)

def main():
    if command == 'release':
        repoutil(results)

if __name__ == '__main__':
    main()
