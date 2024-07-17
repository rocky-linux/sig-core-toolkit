#!/usr/bin/env python3
# -*-:python; coding:utf-8; -*-
# author: Louis Abel <label@rockylinux.org>
# pylint: disable=missing-module-docstring
#
# This script acts as an auditor for a FreeIPA domain. It's primary uses are
# for providing information of a client system and auditing policies, but can
# also be used as a simple query tool. When in audit mode, it will communicate
# with the IPA domain and attempt to get information such as HBAC and SUDO.
# Note that the auditor functionality may require an account with specialized
# privileges.

# Changelog:
#   * Wed Nov 08 2023
#   - Initial version

import os
import sys
import configparser
import socket
import subprocess
import argparse

################################################################################
# This is specifically for audit operations where the client system running the
# audit is not a direct client of the IPA domain. This is either used as a
# fallback if ipalib is not available or if called during "audit". This library
# is installable from EPEL (for RHEL-like machines), or the default Fedora
# repos.
try:
    from python_freeipa import ClientMeta
except ImportError:
    ClientMeta = None

################################################################################
# A system with the (free)ipa-client packages will have this library by
# default. If the system is enrolled, this will work without much of an issue.
# This is the default method of interacting with the API.
try:
    from ipalib import api as libapi
except ImportError:
    libapi = None

if not libapi and not ClientMeta:
    print('No IPA python modules are available')
    sys.exit(1)

################################################################################
# The argument parser should allow us to use sub parsers.
parser = argparse.ArgumentParser(
        description='IPA Auditor and Infolets',
        epilog='Use this with a wrapper to gather client or general IPA audit information')
subparser = parser.add_subparsers(dest='cmd')
subparser.required = True
info_parser = subparser.add_parser('info', epilog='Use this to get IPA client information.')
query_parser = subparser.add_parser('query', epilog='Use this to perform simple IPA queries.')
audit_parser = subparser.add_parser('audit', epilog='Use this to perform audits of IPA policies')
parser.add_argument('--library', type=str, default='ipalib',
                    help='Choose the ipa library to use for the auditor',
                    choices=('ipalib', 'python_freeipa'))

audit_parser.add_argument('--type', type=str, required=True,
                          help='Type of audit: hbac, rbac, group, user',
                          choices=('hbac', 'rbac', 'group', 'user'))
audit_parser.add_argument('--name', type=str, default='',
                          help='Name of the object you want to audit')
audit_parser.add_argument('--deep', action='store_true',
                          help='Name of the object you want to audit')

# all query related subparsers
# pylint: disable=line-too-long
query_subparser = query_parser.add_subparsers(dest='query_cmd')
user_query_parser = query_subparser.add_parser('user', epilog="Use this to get user information.")
user_query_parser.add_argument('-A', '--all', action='store_true', help='Get everything about the user')
user_query_parser.add_argument('name', nargs='?', help='User name')
group_query_parser = query_subparser.add_parser('group', epilog="Use this to get group information.")
group_query_parser.add_argument('-A', '--all', action='store_true', help='Get everything about the group')
group_query_parser.add_argument('name', nargs='?', help='Group name')

known = parser.parse_known_args()
results = parser.parse_args()
command = parser.parse_args().cmd

################################################################################
# Generic classes. These are the classes for very generic operations and
# getting information, usually about the host.
# pylint: disable=too-few-public-methods
class EtcIPADefault:
    """
    Reads just the /etc/ipa/default.conf file that is generated
    """
    @staticmethod
    def read():
        """
        Attempt to read the config file
        """
        if not os.path.exists('/etc/ipa/default.conf'):
            print('File does not exist (/etc/ipa/default.conf)', sys.stderr)
            print('Is this system enrolled to a domain?', sys.stderr)
            sys.exit(1)

        __config = configparser.ConfigParser()
        __config.read('/etc/ipa/default.conf')
        outter_info = {}
        outter_info['local_host_name'] = socket.gethostname()
        outter_info['ipa_joined_name'] = __config['global']['host']
        outter_info['ipa_domain'] = __config['global']['domain']
        outter_info['ipa_realm'] = __config['global']['realm']
        outter_info['registered_dc'] = __config['global']['server']
        return outter_info

class SssctlInfo:
    """
    Uses sssctl to gather minimum required information. Most current
    distributions that support IPA should have this binary available.
    """
    @staticmethod
    def domain_status(ipa_domain):
        """
        Gets the status from sssctl
        """
        sssctl_cmd = f'/usr/sbin/sssctl domain-status -o {ipa_domain}'
        if not os.path.exists('/usr/sbin/sssctl'):
            return 'sssctl command not found'

        if not os.getuid() == 0:
            return 'Unknown; root required'

        if sys.version_info[:2] <= (3, 6):
            processor = subprocess.run(args=sssctl_cmd,
                                       shell=True, check=False,
                                       universal_newlines=True,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
        else:
            processor = subprocess.run(args=f'/usr/sbin/sssctl domain-status -o {ipa_domain}',
                                       check=False, capture_output=True, text=True, shell=True)

        domain_status_out = processor.stdout.strip().split(':')[1].strip()
        return domain_status_out

    @staticmethod
    def current_dc(ipa_domain):
        """
        Gets the current connected DC
        """
        sssctl_cmd = f'/usr/sbin/sssctl domain-status -a {ipa_domain} | grep IPA'
        if not os.path.exists('/usr/sbin/sssctl'):
            return 'sssctl command not found'

        if not os.getuid() == 0:
            return 'Unknown; root required'

        if sys.version_info[:2] <= (3, 6):
            processor = subprocess.run(args=sssctl_cmd,
                                       shell=True, check=False,
                                       universal_newlines=True,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
        else:
            # pylint: disable=line-too-long
            processor = subprocess.run(args=f'/usr/sbin/sssctl domain-status -a {ipa_domain} | grep IPA',
                                       check=False, capture_output=True, text=True, shell=True)

        current_dc_out = processor.stdout.strip().split(':')[1].strip()
        return current_dc_out

class IPACalls:
    """
    IPA specific API calls. info, query, audit should all call in this.
    """
    ################################################################################
    # Kerberos
    @staticmethod
    def quick_host_kinit():
        """
        brings in the host kerb ticket
        """
        etc_ipa_default = EtcIPADefault.read()
        # pylint: disable=line-too-long
        kinit_cmd = f"/usr/bin/kinit -kt /etc/krb5.keytab host/{etc_ipa_default['local_host_name']}@{etc_ipa_default['ipa_realm']}"
        err_code = subprocess.run(args=kinit_cmd, shell=True, check=False)
        if err_code.returncode != 0:
            print('We could not run kdestroy on the host.', sys.stderr)
            sys.exit(1)

    @staticmethod
    def quick_host_kdestroy():
        """
        destroys the host kerb ticket
        """
        etc_ipa_default = EtcIPADefault.read()
        # pylint: disable=line-too-long
        kdestroy_cmd = f"/usr/bin/kdestroy -p host/{etc_ipa_default['local_host_name']}@{etc_ipa_default['ipa_realm']}"
        err_code = subprocess.run(args=kdestroy_cmd, shell=True, check=False)
        if err_code.returncode != 0:
            print('We could not run kinit as the host.', sys.stderr)
            sys.exit(1)

    # End kerberos
    ################################################################################

    ################################################################################
    # Static IPA calls
    @staticmethod
    def get_host_groups(api, host):
        """
        Gets the list of hostgroups this client is a part of
        """
        if api:
            api_results = api.host_show(host, all=True)['result']['memberof_hostgroup']
            return api_results
        return ['Unknown, no kerb ticket']

    # End static IPA calls
    ################################################################################

class IPAInfo:
    """
    Get IPA specific information for a client.
    """
    @staticmethod
    def get_basic_ipa_info(api):
        """
        Gets the actual info
        """
        etc_ipa_default = EtcIPADefault.read()
        domain_status = SssctlInfo.domain_status(etc_ipa_default['ipa_domain'])
        current_dc = SssctlInfo.current_dc(etc_ipa_default['ipa_domain'])
        current_hostname = etc_ipa_default['local_host_name']
        hostgroups = '\n                    '.join(IPACalls.get_host_groups(api, current_hostname))
        output_dict = {
                'Local host name:': etc_ipa_default['local_host_name'],
                'Joined to domain:': etc_ipa_default['ipa_domain'],
                'Joined as:': etc_ipa_default['ipa_joined_name'],
                'Registered DC:': etc_ipa_default['registered_dc'],
                'Current DC:': current_dc,
                'Domain status:': domain_status,
                'Host Group(s):': hostgroups,
        }
        for key, value in output_dict.items():
            print(f'{key: <20}{value}')

    @staticmethod
    def basic_ipa_info(api):
        """
        Basic IPA info (aka ipainfo).
        """
        IPAInfo.get_basic_ipa_info(api)

################################################################################
# Specific classes. These are for classes with a very specific use case. Mainly
# for working with the auditor or query system.
class IPAAudit:
    """
    This is for getting audit data

    RBAC, HBAC. "deep" option should recurse down groups and users
    """
    @staticmethod
    def entry(api, control, name, deep):
        """
        Gets us started on the audit
        """
        if control == 'hbac':
            IPAAudit.hbac_pull(api, name, deep)
        if control == 'rbac':
            IPAAudit.rbac_pull(api, name, deep)
        if control == 'user':
            IPAAudit.user_pull(api, name, deep)
        if control == 'group':
            IPAAudit.group_pull(api, name, deep)

    @staticmethod
    def user_pull(api, name, deep):
        """
        Gets requested rbac info
        """
        print()

    @staticmethod
    def group_pull(api, name, deep):
        """
        Gets requested rbac info
        """
        print()

    @staticmethod
    def hbac_pull(api, name, deep):
        """
        Gets requested rbac info
        """
        try:
            hbac_results = IPAQuery.hbac_data(api, name)
        except:
            print(f'Could not find {name}', sys.stderr)
            sys.exit(1)

        hbac_description = '' if not hbac_results.get('description', None) else hbac_results['description'][0]
        hbac_svcs = '' if not hbac_results.get('memberservice_hbacsvc', None) else '\n                '.join(hbac_results['memberservice_hbacsvc'])
        hbac_svcs_groups = '' if not hbac_results.get('memberservice_hbacsvcgroup', None) else '\n                '.join(hbac_results['memberservice_hbacsvcgroup'])
        users = '' if not hbac_results.get('memberuser_user', None) else '\n '.join(hbac_results['memberuser_user'])
        hosts = '' if not hbac_results.get('memberhost_host', None) else '\n '.join(hbac_results['memberhost_host'])
        groups = '' if not hbac_results.get('memberuser_group', None) else '\n                '.join(hbac_results['memberuser_group'])
        hostgroups = '' if not hbac_results.get('memberhost_hostgroup', None) else '\n                '.join(hbac_results['memberhost_hostgroup'])

    @staticmethod
    def rbac_pull(api, name, deep):
        """
        Gets requested rbac info
        """
        try:
            rbac_results = IPAQuery.role_data(api, name)
        except:
            print(f'Could not find {name}', sys.stderr)
            sys.exit(1)

        # pylint: disable=line-too-long
        rbac_description = '' if not rbac_results.get('description', None) else rbac_results['description'][0]
        rbac_privs = '' if not rbac_results.get('memberof_privilege', None) else '\n                '.join(rbac_results['memberof_privilege'])
        users = '' if not rbac_results.get('member_user', None) else '\n                '.join(rbac_results['member_user'])
        hosts = '' if not rbac_results.get('member_host', None) else '\n                '.join(rbac_results['member_host'])
        groups = '' if not rbac_results.get('member_group', None) else '\n                '.join(rbac_results['member_group'])
        hostgroups = '' if not rbac_results.get('member_hostgroup', None) else '\n                '.join(rbac_results['member_hostgroup'])

        starter_rbac = {
                'Role Name:': name,
                'Description:': rbac_description,
                'Privileges:': rbac_privs,
                'Users:': users,
                'Groups:': groups,
                'Hosts:': hosts,
                'Hosts Groups:': hostgroups,
        }
        print('RBAC Information')
        print('----------------------------------------')
        for key, value in starter_rbac.items():
            if len(value) > 0:
                print(f'{key: <16}{value}')
        print('')

        if deep:
            user_list = [] if not rbac_results.get('member_user', None) else rbac_results['member_user']
            group_list = [] if not rbac_results.get('member_group', None) else rbac_results['member_group']
            priv_list = [] if not rbac_results.get('memberof_privilege', None) else rbac_results['memberof_privilege']
            IPAAudit.role_deep_list(api, user_list, group_list, priv_list)

    @staticmethod
    # pylint: disable=dangerous-default-value
    def hbac_deep_list(api, users, groups, privs):
        """
        Does recursive digging on the control provided
        """
        print()

    @staticmethod
    # pylint: disable=dangerous-default-value
    def role_deep_list(api, users, groups, privs):
        """
        Does recursive digging on the users provided
        """
        starting_perms = []
        for priv in privs:
            data = IPAQuery.priv_data(api, priv)
            description = '' if not data.get('description', None) else data['description'][0]
            permlist = '' if not data.get('memberof_permission', None) else data['memberof_permission']
            if len(permlist) > 0:
                for perm in permlist:
                    if perm not in starting_perms:
                        starting_perms.append(perm)

        print(f'Permissions Applied to this Role')
        print('----------------------------------------')
        for item in starting_perms:
            print(item)
        print('')

        starting_user_list = users
        for group in groups:
            data = IPAQuery.group_data(api, group)
            description = '' if not data.get('description', None) else data['description'][0]
            userlist = '' if not data.get('member_user', None) else data['member_user']
            ind_userlist = '' if not data.get('memberindirect_user', None) else data['memberindirect_user']
            grouplist = '' if not data.get('member_group', None) else '\n                '.join(data['member_group'])

            user_list = []
            ind_user_list = []
            if len(userlist) > 0:
                for user in userlist:
                    user_list.append(f'{user}')
                    if user not in starting_user_list:
                        starting_user_list.append(user)
            if len(ind_userlist) > 0:
                for user in ind_userlist:
                    ind_user_list.append(f'{user}')
                    if user not in starting_user_list:
                        starting_user_list.append(user)

            user_list_join = '\n                '.join(user_list)
            ind_user_list_join = '\n                '.join(ind_user_list)

            group_dict = {
                    'Description:': description,
                    'Users:': user_list_join,
                    'Indirect Users:': ind_user_list_join,
                    'Groups:': grouplist,
            }
            print(f'Group: {group}')
            print('----------------------------------------')
            for key, value in group_dict.items():
                if len(value) > 0:
                    print(f'{key: <16}{value}')
            print('')

        final_user_list = {}
        for user in starting_user_list:
            data = IPAQuery.user_data(api, user)
            this_user = IPAQuery.user_data(api, user)
            fullname = f"{this_user['givenname'][0]} {this_user['sn'][0]}"
            final_user_list[user] = fullname

        if len(starting_user_list) > 0:
            print('Full List of Users for this role')
            print('----------------------------------------')
        for key, value in final_user_list.items():
            if len(value) > 0:
                print(f'{key: <24}{value}')

    @staticmethod
    def user_deep_list(api, user):
        """
        Does a recursive dig on a user
        """

    @staticmethod
    def group_deep_list(api, group):
        """
        Does a recursive dig on a group
        """

class IPAQuery:
    """
    This is for getting query data
    """
    @staticmethod
    def entry(api, control, name, deep):
        """
        Gets us started on the query
        """
        #user_data = IPAQuery.user_data(api, name)
        if control == 'user':
            IPAQuery.user_pull(api, name, deep)
        if control == 'group':
            IPAQuery.group_pull(api, name, deep)

    @staticmethod
    def user_pull(api, name, deep):
        """
        Gets requested rbac info
        """
        user_results = IPAQuery.user_data(api, name)
        uid = user_results['uid'][0]
        uid_number = user_results['uidnumber'][0]
        gid_number = user_results['gidnumber'][0]
        first_name = user_results['givenname'][0]
        last_name = user_results['sn'][0]
        homedir = user_results['homedirectory'][0]
        loginshell = user_results['loginshell'][0]
        full_name = f'{first_name} {last_name}'
        krbprincipal = user_results['krbprincipalname'][0]
        groups = ','.join(user_results['memberof_group'])
        getent_string = f'{uid}:x:{uid_number}:{gid_number}:{full_name}:{homedir}:{loginshell}'
        if not deep:
            print(getent_string)
        else:
            outter = f"""
unixname:{uid}
uid:{uid_number}
gid:{gid_number}
gecos:{full_name}
displayName:{full_name}
home:{homedir}
shell:{loginshell}
userPrincipalName:{krbprincipal}
memberOf:{groups}
            """
            print(outter)


    @staticmethod
    def group_pull(api, name, deep):
        """
        Gets requested rbac info
        """
        print()

    @staticmethod
    def user_data(api, user):
        """
        Returns all user data
        """
        return api.user_show(user)['result']

    @staticmethod
    def group_data(api, group):
        """
        Returns all group data
        """
        return api.group_show(group)['result']

    @staticmethod
    def hostgroup_data(api, group):
        """
        Returns all group data
        """
        return api.hostgroup_show(group)['result']

    @staticmethod
    def role_data(api, role):
        """
        Returns all role data
        """
        return api.role_show(role)['result']

    @staticmethod
    def priv_data(api, priv):
        """
        Returns all role data
        """
        return api.privilege_show(priv)['result']

    @staticmethod
    def hbac_data(api, hbac):
        """
        Returns all hbac data
        """
        return api.hbacrule_show(hbac)['result']

    @staticmethod
    def hbacsvcgroup_data(api, hbacsvcgroup):
        """
        Returns all hbac service group data
        """
        return api.hbacsvcgroup_show(hbacsvcgroup)['result']

# start main
def get_api(ipa_library='ipalib'):
    """
    Gets and returns the right API entrypoint
    """
    # This is unfortunately hacky.
    if ipa_library == 'ipalib':
        # When root, use the hostkeytab
        if os.getuid() == 0:
            IPACalls.quick_host_kinit()
        api = libapi
        try:
            api.bootstrap(context="custom")
            api.finalize()
            api.Backend.rpcclient.connect()
            command_api = api.Command
        except:
            print('WARNING: No kerberos credentials\n')
            command_api = None
    elif ipa_library == 'python_freeipa':
        print()
    else:
        print('Unsupported ipa library', sys.stderr)
        sys.exit(1)

    return command_api

def main():
    """
    Main function entrypoint
    """
    command_api = get_api()
    if command == 'audit':
        IPAAudit.entry(command_api, results.type, results.name, results.deep)
    elif command == 'info':
        IPAInfo.basic_ipa_info(command_api)
    elif command == 'query':
        IPAQuery.entry(command_api, results.query_cmd, results.name, results.all)

    # When root, kdestroy the host keytab
    if os.getuid() == 0:
        IPACalls.quick_host_kdestroy()

if __name__ == '__main__':
    main()
