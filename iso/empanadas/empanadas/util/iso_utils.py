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

# This is for treeinfo
from configparser import ConfigParser
from productmd.common import SortedConfigParser
from productmd.images import Image
from productmd.extra_files import ExtraFiles
import productmd.treeinfo
# End treeinfo

from jinja2 import Environment, FileSystemLoader

from empanadas.common import Color, _rootdir

class IsoBuild:
    """
    This helps us build the generic ISO's for a Rocky Linux release. In
    particular, this is for the boot images.

    While there is a function for building the DVD and live images, this not
    the main design of this class. The other functions can be called on their
    own to facilitate those particular builds.
    """
    def __init__(
            self,
            rlvars,
            config,
            major,
            rc: bool = False,
            force_unpack: bool = False,
            isolation: str = 'auto',
            compose_dir_is_here: bool = False,
            image=None,
            logger=None
    ):
        self.image = image
        self.fullname = rlvars['fullname']
        self.distname = config['distname']
        self.shortname = config['shortname']
        # Relevant config items
        self.major_version = major
        self.compose_dir_is_here = compose_dir_is_here
        self.disttag = config['dist']
        self.date_stamp = config['date_stamp']
        self.timestamp = time.time()
        self.compose_root = config['compose_root']
        self.compose_base = config['compose_root'] + "/" + major
        self.iso_drop = config['compose_root'] + "/" + major + "/isos"
        self.current_arch = config['arch']
        self.required_pkgs = rlvars['iso_map']['required_pkgs']
        self.mock_work_root = config['mock_work_root']
        self.lorax_result_root = config['mock_work_root'] + "/" + "lorax"
        self.mock_isolation = isolation
        self.iso_map = rlvars['iso_map']
        self.release_candidate = rc
        self.force_unpack = force_unpack

        # Relevant major version items
        self.release = rlvars['revision']
        self.minor_version = rlvars['minor']
        self.revision = rlvars['revision'] + "-" + rlvars['rclvl']
        self.rclvl = rlvars['rclvl']
        self.repos = rlvars['iso_map']['repos']
        self.repo_base_url = config['repo_base_url']
        self.project_id = rlvars['project_id']

        self.extra_files = rlvars['extra_files']

        self.staging_dir = os.path.join(
                    config['staging_root'],
                    config['category_stub'],
                    self.revision
        )

        # Templates
        file_loader = FileSystemLoader(f"{_rootdir}/templates")
        self.tmplenv = Environment(loader=file_loader)

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

        self.iso_work_dir = os.path.join(
                self.compose_latest_dir,
                "work/iso",
                config['arch']
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
        self.repolist = self.build_repo_list()
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

        self.iso_build()

        self.log.info('Compose repo directory: %s' % sync_root)
        self.log.info('ISO Build Logs: /var/lib/mock/{}-{}-{}/result'.format(
            self.shortname, self.major_version, self.current_arch)
        )
        self.log.info('ISO Build completed.')

    def build_repo_list(self):
        """
        Builds the repo dictionary
        """
        repolist = []
        for name in self.repos:
            if not self.compose_dir_is_here:
                constructed_url = '{}/{}/repo/hashed-{}/{}'.format(
                        self.repo_base_url,
                        self.project_id,
                        name,
                        self.current_arch
                )
            else:
                constructed_url = 'file://{}/{}/{}/os'.format(
                        self.compose_latest_sync,
                        name,
                        self.current_arch
                )


            repodata = {
                'name': name,
                'url': constructed_url
            }

            repolist.append(repodata)

        return repolist

    def iso_build(self):
        """
        This does the general ISO building for the current running
        architecture. This generates the mock config and the general script
        needed to get this part running.
        """
        # Check for local build, build accordingly
        # Check for arch specific build, build accordingly
        # local AND arch cannot be used together, local supersedes. print
        # warning.
        self.generate_iso_scripts()
        self.run_lorax()

    def generate_iso_scripts(self):
        """
        Generates the scripts needed to be ran to run lorax in mock as well as
        package up the results.
        """
        self.log.info('Generating ISO configuration and scripts')
        mock_iso_template = self.tmplenv.get_template('isomock.tmpl.cfg')
        mock_sh_template = self.tmplenv.get_template('isobuild.tmpl.sh')
        iso_template = self.tmplenv.get_template('buildImage.tmpl.sh')

        mock_iso_path = '/var/tmp/lorax-' + self.major_version + '.cfg'
        mock_sh_path = '/var/tmp/isobuild.sh'
        iso_template_path = '/var/tmp/buildImage.sh'

        rclevel = ''
        if self.release_candidate:
            rclevel = '-' + self.rclvl

        mock_iso_template_output = mock_iso_template.render(
                arch=self.current_arch,
                major=self.major_version,
                fullname=self.fullname,
                shortname=self.shortname,
                required_pkgs=self.required_pkgs,
                dist=self.disttag,
                repos=self.repolist,
                user_agent='{{ user_agent }}',
        )

        mock_sh_template_output = mock_sh_template.render(
                arch=self.current_arch,
                major=self.major_version,
                isolation=self.mock_isolation,
                builddir=self.mock_work_root,
                shortname=self.shortname,
        )

        iso_template_output = iso_template.render(
                arch=self.current_arch,
                major=self.major_version,
                minor=self.minor_version,
                shortname=self.shortname,
                repos=self.repolist,
                variant=self.iso_map['variant'],
                lorax=self.iso_map['lorax_removes'],
                distname=self.distname,
                revision=self.release,
                rc=rclevel,
                builddir=self.mock_work_root,
                lorax_work_root=self.lorax_result_root,
        )

        mock_iso_entry = open(mock_iso_path, "w+")
        mock_iso_entry.write(mock_iso_template_output)
        mock_iso_entry.close()

        mock_sh_entry = open(mock_sh_path, "w+")
        mock_sh_entry.write(mock_sh_template_output)
        mock_sh_entry.close()

        iso_template_entry = open(iso_template_path, "w+")
        iso_template_entry.write(iso_template_output)
        iso_template_entry.close()

        os.chmod(mock_sh_path, 0o755)
        os.chmod(iso_template_path, 0o755)

    def run_lorax(self):
        """
        This actually runs lorax on this system. It will call the right scripts
        to do so.
        """
        lorax_cmd = '/bin/bash /var/tmp/isobuild.sh'
        self.log.info('Starting lorax...')

        p = subprocess.call(shlex.split(lorax_cmd))
        if p != 0:
            self.log.error('An error occured during execution.')
            self.log.error('See the logs for more information.')
            raise SystemExit()

    def run_image_build(self, arch):
        """
        Builds the other images
        """
        print()

    def run_boot_sync(self, arch, force_sync):
        """
        This unpacks into BaseOS/$arch/os, assuming there's no data actually
        there. There should be checks.

        1. Sync from work/$arch/lorax to work/$arch/dvd
        2. Sync from work/$arch/lorax to work/$arch/minimal
        3. Sync from work/$arch/lorax to BaseOS/$arch/os
        4. Modify (3) .treeinfo
        5. Modify (1) .treeinfo, keep out boot.iso checksum
        6. Create a .treeinfo for AppStream
        """
        self.sync_boot(arch, force_sync)

    def sync_boot(self, arch, force_sync):
        """
        Syncs whatever is in work/$arch/lorax to BaseOS/$arch/os
        """
        self.log.info('Syncing lorax to dvd directory...')
        self.log.info('Syncing lorax to %s directory...' % self.iso_map['variant'])

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

    def build_extra_iso(self):
        """
        Builds DVD images based on the data created from the initial lorax on
        each arch. This should NOT be called during the usual run() section.
        """
        print()

    def generate_graft_points(self):
        """
        Get a list of packages for an extras ISO. This should NOT be called
        during the usual run() section.
        """
        print()

class LiveBuild:
    """
    This helps us build the live images for Rocky Linux.
    """
