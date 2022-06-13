"""
Builds ISO's for Rocky Linux.

Louis Abel <label AT rockylinux.org>
"""

import logging
import sys
import os
import os.path
import subprocess
import shlex
import time
import re
from productmd.common import SortedConfigParser
from common import Color

class IsoBuild:
    """
    This helps us build the generic ISO's for a Rocky Linux release. In
    particular, this is for the boot and dvd images.

    Live images are built in another class.
    """
    def __init__(
            self,
            rlvars,
            config,
            major,
            host=None,
            image=None,
            arch=None,
            logger=None
    ):
        self.arch = arch
        self.image = image
        self.host = host
        self.fullname = rlvars['fullname']
        # Relevant config items
        self.major_version = major
        self.disttag = config['dist']
        self.date_stamp = config['date_stamp']
        self.timestamp = time.time()
        self.compose_root = config['compose_root']
        self.compose_base = config['compose_root'] + "/" + major
        self.iso_drop = config['compose_root'] + "/" + major + "/isos"
        self.current_arch = config['arch']
        self.extra_files = rlvars['extra_files']

        # Relevant major version items
        self.revision = rlvars['revision'] + "-" + rlvars['rclvl']
        self.arches = rlvars['allowed_arches']

        self.staging_dir = os.path.join(
                    config['staging_root'],
                    config['category_stub'],
                    self.revision
        )

        self.compose_latest_dir = os.path.join(
                config['compose_root'],
                major,
                "latest-Rocky-{}".format(major)
        )

        self.compose_latest_sync = os.path.join(
                self.compose_latest_dir,
                "compose"
        )

        self.compose_log_dir = os.path.join(
                self.compose_latest_dir,
                "work/logs"
        )

        # This is temporary for now.
        if logger is None:
            self.log = logging.getLogger("iso")
            self.log.setLevel(logging.INFO)
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                    '%(asctime)s :: %(name)s :: %(message)s',
                    '%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.log.addHandler(handler)

        self.log.info('iso build init')
        self.log.info(self.revision)

    def run(self):
        work_root = os.path.join(
                self.compose_latest_dir,
                'work'
        )
        sync_root = self.compose_latest_sync

        log_root = os.path.join(
                work_root,
                "logs"
        )

        self.iso_build(
                sync_root,
                work_root,
                log_root,
                self.arch,
                self.host
        )

        self.log.info('Compose repo directory: %s' % sync_root)
        self.log.info('ISO Build Logs: %s' % log_root)
        self.log.info('ISO Build completed.')

    def iso_build(self, sync_root, work_root, log_root, arch, host):
        """
        Calls out the ISO builds to the individual hosts listed in the map.
        Each architecture is expected to build their own ISOs, similar to
        runroot operations of koji and pungi.

        It IS possible to run locally, but that would mean this only builds
        ISOs for the architecture of the running machine. Please keep this in
        mind when stating host=local.
        """
        # Check for local build, build accordingly
        # Check for arch specific build, build accordingly
        # local AND arch cannot be used together, local supersedes. print
        # warning.
        local_only = False
        if 'local' in self.host:
            local_only = True

        arch = self.arch.copy()
        if local_only and self.arch:
            self.log.warn('You cannot set local build AND an architecture.')
            self.log.warn('The architecture %s will be set' % self.current_arch)
            arch = self.current_arch

    def iso_build_local(self, sync_root, work_root, log_root):
        """
        Local iso builds only. Architecture is locked.
        """
        print()

    def iso_build_remote(self, sync_root, work_root, log_root, arch):
        """
        Remote ISO builds. Architecture is all or single.
        """
        print()

    def generate_iso_scripts(self):
        """
        Generates the scripts needed to be ran in the mock roots
        """
        print()

    def treeinfo_write(self):
        """
        Ensure treeinfo is written correctly
        """
        print()

    def discinfo_write(self):
        """
        Ensure discinfo is written correctly
        """
        #with open(file_path, "w") as f:
        #    f.write("%s\n" % self.timestamp)
        #    f.write("%s\n" % self.fullname)
        #    f.write("%s\n" % self.arch)
        #    if disc_numbers:
        #        f.write("%s\n" % ",".join([str(i) for i in disc_numbers]))
        print()

    def write_media_repo(self):
        """
        Ensure media.repo exists
        """
        data = [
            "[InstallMedia]",
            "name=%s" % self.fullname,
            "mediaid=%s" % self.timestamp,
            "metadata_expire=-1",
            "gpgcheck=0",
            "cost=500",
            "",
        ]


    def generate_graft_points(self):
        """
        Get a list of packages for an ISO
        """
        print()


class LiveBuild:
    """
    This helps us build the live images for Rocky Linux.
    """
