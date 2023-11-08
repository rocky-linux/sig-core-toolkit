#!/usr/bin/env python3
# -*-:python; coding:utf-8; -*-
# author: Louis Abel <label@rockylinux.org>
#
# This scripts attempts to be an adinfo lookalike. This does not implement all
# features that are available.

import os
import sys
import socket
import configparser
import subprocess
#from python_freeipa import ClientMeta
try:
    from ipalib import api
except ImportError as exc:
    raise ImportError('No IPA libraries found.') from exc

try:
    api.bootstrap(context="custom")
    api.finalize()
    # pylint: disable=no-member
    api.Backend.rpcclient.connect()
    api_access = True
except:
    print('WARNING: No kerberos credentials')
    api_access = False

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
            print('File does not exist (/etc/ipa/default.conf)')
            sys.exit(1)

        __config = configparser.ConfigParser()
        __config.read('/etc/ipa/default.conf')
        outter_info = {}
        outter_info['local_host_name'] = socket.gethostname()
        outter_info['ipa_joined_name'] = __config['global']['host']
        outter_info['ipa_domain'] = __config['global']['domain']
        outter_info['registered_dc'] = __config['global']['server']
        return outter_info

class SssctlInfo:
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

        if sys.version_info <= (3, 6):
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

        if sys.version_info <= (3, 6):
            processor = subprocess.run(args=sssctl_cmd,
                                       shell=True, check=False,
                                       universal_newlines=True,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
        else:
            processor = subprocess.run(args=f'/usr/sbin/sssctl domain-status -a {ipa_domain} | grep IPA',
                                       check=False, capture_output=True, text=True, shell=True)

        current_dc_out = processor.stdout.strip().split(':')[1].strip()
        return current_dc_out

class IPAInfo:
    """
    Get IPA specific information
    """
    @staticmethod
    def get_host_groups(host):
        if api_access:
            results = api.Command.host_show(host, all=True)['result']['memberof_hostgroup']
            return results
        return ['Unknown']

    @staticmethod
    def get_ipa_info():
        """
        Gets the actual info
        """

        etc_ipa_default = EtcIPADefault.read()
        domain_status = SssctlInfo.domain_status(etc_ipa_default['ipa_domain'])
        current_dc = SssctlInfo.current_dc(etc_ipa_default['ipa_domain'])
        current_hostname = etc_ipa_default['local_host_name']
        current_domain = etc_ipa_default['ipa_domain']
        hostgroups = '\n                   '.join(IPAInfo.get_host_groups(current_hostname))
        output = f'''
Local host name:   {etc_ipa_default['local_host_name']}
Joined to domain:  {etc_ipa_default['ipa_domain']}
Joined as:         {etc_ipa_default['ipa_joined_name']}
Registered DC:     {etc_ipa_default['registered_dc']}
Current DC:        {current_dc}
Domain Status:     {domain_status}
Host Group(s):     {hostgroups}
'''
        print(output)


def main():
    IPAInfo.get_ipa_info()

if __name__ == '__main__':
    main()
