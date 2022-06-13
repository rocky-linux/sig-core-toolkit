# All imports are here
import os
import platform
import time
import glob
import rpm
import yaml
import logging

# These are a bunch of colors we may use in terminal output
class Color:
    RED = '\033[91m'
    GREEN = '\033[92m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    UNDERLINE = '\033[4m'
    BOLD = '\033[1m'
    END = '\033[0m'

# vars and additional checks
rldict = {}
sigdict = {}
config = {
    "rlmacro": rpm.expandMacro('%rhel'),
    "dist": 'el' + rpm.expandMacro('%rhel'),
    "arch": platform.machine(),
    "date_stamp": time.strftime("%Y%m%d.%H%M%S", time.localtime()),
    "compose_root": "/mnt/compose",
    "staging_root": "/mnt/repos-staging",
    "production_root": "/mnt/repos-production",
    "category_stub": "mirror/pub/rocky",
    "sig_category_stub": "mirror/pub/sig",
    "repo_base_url": "https://yumrepofs.build.resf.org/v1/projects",
    "container": "centos:stream9"
}

# Importing the config from yaml
for conf in glob.iglob('configs/*.yaml'):
    with open(conf, 'r', encoding="utf-8") as file:
        rldict.update(yaml.safe_load(file))

# Import all SIG configs from yaml
for conf in glob.iglob('sig/*.yaml'):
    with open(conf, 'r', encoding="utf-8") as file:
        sigdict.update(yaml.safe_load(file))

# The system needs to be a RHEL-like system. It cannot be Fedora or SuSE.
#if "%rhel" in config['rlmacro']:
#    raise SystemExit(Color.BOLD + 'This is not a RHEL-like system.' + Color.END
#            + '\n\nPlease verify you are running on a RHEL-like system that is '
#            'not Fedora nor SuSE. This means that the %rhel macro will be '
#            'defined with a value equal to the version you are targetting. RHEL'
#            ' and its derivatives have this set.')


# These will be set in their respective var files
#REVISION = rlvars['revision'] + '-' + rlvars['rclvl']
#rlvars = rldict[rlver]
#rlvars = rldict[rlmacro]
#COMPOSE_ISO_WORKDIR = COMPOSE_ROOT + "work/" + arch + "/" + date_stamp
