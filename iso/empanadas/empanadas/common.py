# All imports are here
import glob
import platform
import time
from collections import defaultdict
from attrs import define, field


import rpm
import yaml


# An implementation from the Fabric python library
class AttributeDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttributeDict, self).__init__(*args, **kwargs)
        for key, value in self.items():
            if isinstance(value, dict):
                self[key] = AttributeDict(value)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            value = AttributeDict(value)
        super(AttributeDict, self).__setitem__(key, value)


# These are a bunch of colors we may use in terminal output
class Color:
    RED = "\033[91m"
    GREEN = "\033[92m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    DARKCYAN = "\033[36m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    UNDERLINE = "\033[4m"
    BOLD = "\033[1m"
    END = "\033[0m"
    INFO = "[" + BOLD + GREEN + "INFO" + END + "] "
    WARN = "[" + BOLD + YELLOW + "WARN" + END + "] "
    FAIL = "[" + BOLD + RED + "FAIL" + END + "] "
    STAT = "[" + BOLD + CYAN + "STAT" + END + "] "


# vars and additional checks
rldict = AttributeDict()
sigdict = AttributeDict()
config = {
    "rlmacro": rpm.expandMacro("%rhel"),
    "dist": "el" + rpm.expandMacro("%rhel"),
    "arch": platform.machine(),
    "date_stamp": time.strftime("%Y%m%d.%H%M%S", time.localtime()),
    "compose_root": "/mnt/compose",
    "staging_root": "/mnt/repos-staging",
    "production_root": "/mnt/repos-production",
    "category_stub": "mirror/pub/rocky",
    "sig_category_stub": "mirror/pub/sig",
    "repo_base_url": "https://yumrepofs.build.resf.org/v1/projects",
    "staging_base_url": "https://dl.rockylinux.org/stg/rocky",
    "mock_work_root": "/builddir",
    "container": "centos:stream9",
    "distname": "Rocky Linux",
    "shortname": "Rocky",
    "translators": {
        "x86_64": "amd64",
        "aarch64": "arm64",
        "ppc64le": "ppc64le",
        "s390x": "s390x",
        "i686": "386",
    },
    "aws_region": "us-east-2",
    "bucket": "resf-empanadas",
    "bucket_url": "https://resf-empanadas.s3.us-east-2.amazonaws.com",
}

# Importing the config from yaml
import importlib_resources

_rootdir = importlib_resources.files("empanadas")

for conf in glob.iglob(f"{_rootdir}/configs/*.yaml"):
    with open(conf, "r", encoding="utf-8") as file:
        rldict.update(yaml.safe_load(file))

# Import all SIG configs from yaml
for conf in glob.iglob(f"{_rootdir}/sig/*.yaml"):
    with open(conf, "r", encoding="utf-8") as file:
        sigdict.update(yaml.safe_load(file))

# The system needs to be a RHEL-like system. It cannot be Fedora or SuSE.
# if "%rhel" in config['rlmacro']:
#    raise SystemExit(Color.BOLD + 'This is not a RHEL-like system.' + Color.END
#            + '\n\nPlease verify you are running on a RHEL-like system that is '
#            'not Fedora nor SuSE. This means that the %rhel macro will be '
#            'defined with a value equal to the version you are targetting. RHEL'
#            ' and its derivatives have this set.')


# These will be set in their respective var files
# REVISION = rlvars['revision'] + '-' + rlvars['rclvl']
# rlvars = rldict[rlver]
# rlvars = rldict[rlmacro]
# COMPOSE_ISO_WORKDIR = COMPOSE_ROOT + "work/" + arch + "/" + date_stamp


ALLOWED_TYPE_VARIANTS = {
    "Azure": ["Base", "LVM"],
    "Container": ["Base", "Minimal", "UBI", "WSL", "Toolbox"],
    "EC2": ["Base", "LVM"],
    "GenericCloud": ["Base", "LVM"],
    "Vagrant": ["Libvirt", "Vbox", "VMware"],
    "OCP": ["Base"],
    "SBC": ["RaspberryPi", "GenericArm"],
    "WSL": ["Base"]
}


def valid_type_variant(_type: str, variant: str = "") -> bool:
    if _type not in ALLOWED_TYPE_VARIANTS:
        raise Exception(f"Type is invalid: ({_type}, {variant})")
    if ALLOWED_TYPE_VARIANTS[_type] is None:
        if variant is not None:
            raise Exception(f"{_type} Type expects no variant type.")
        return True
    if variant not in ALLOWED_TYPE_VARIANTS[_type]:
        if variant and variant.capitalize() in ALLOWED_TYPE_VARIANTS[_type]:
            raise Exception(
                f"Capitalization mismatch. Found: ({_type}, {variant}). Expected: ({_type}, {variant.capitalize()})"
            )
        raise Exception(
            f"Type/Variant Combination is not allowed: ({_type}, {variant})"
        )
    return True


@define(kw_only=True)
class Architecture:
    name: str = field()
    version: str = field()
    major: int = field(converter=int)
    minor: int = field(converter=int)

    @classmethod
    def from_version(cls, architecture: str, version: str):
        major, minor = str.split(version, ".")
        if architecture not in rldict[major]["allowed_arches"]:
            print("Invalid architecture/version combo, skipping")
            exit()
        return cls(name=architecture, version=version, major=major, minor=minor)
