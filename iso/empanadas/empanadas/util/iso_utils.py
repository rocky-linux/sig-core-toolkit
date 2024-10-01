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
import tarfile
import shutil

# lazy person's s3 parser
#import requests
#import json
#import xmltodict
# if we can access s3
#import boto3
# relative_path, compute_file_checksums
import kobo.shortcuts
from fnmatch import fnmatch

# This is for treeinfo
from configparser import ConfigParser
from productmd.common import SortedConfigParser
from productmd.images import Image
from productmd.extra_files import ExtraFiles
import productmd.treeinfo
# End treeinfo

from jinja2 import Environment, FileSystemLoader

from empanadas.common import Color, _rootdir
from empanadas.util import Shared, ArchCheck, Idents

class IsoBuild:
    """
    This helps us build the generic ISO's for a Rocky Linux release. In
    particular, this is for the boot images.

    There are functions to build the DVD (and potentially other) images. Each
    particular build or process starts with "run" in their name.
    """
    def __init__(
            self,
            rlvars,
            config,
            major,
            arch=None,
            rc: bool = False,
            s3: bool = False,
            force_download: bool = False,
            force_unpack: bool = False,
            isolation: str = 'auto',
            extra_iso=None,
            extra_iso_mode: str = 'local',
            compose_dir_is_here: bool = False,
            hashed: bool = False,
            updated_image: bool = False,
            image_increment: str = '0',
            image=None,
            s3_region=None,
            s3_bucket=None,
            s3_bucket_url=None,
            logger=None
    ):
        self.image = image
        self.fullname = rlvars['fullname']
        self.distname = config['distname']
        self.shortname = config['shortname']
        # Relevant config items
        self.major_version = major
        self.compose_dir_is_here = compose_dir_is_here
        self.disttag = rlvars['disttag']
        self.date_stamp = config['date_stamp']
        self.timestamp = time.time()
        self.compose_root = config['compose_root']
        self.compose_base = config['compose_root'] + "/" + major
        self.current_arch = config['arch']
        #self.required_pkgs = rlvars['iso_map']['lorax']['required_pkgs']
        self.mock_work_root = config['mock_work_root']
        self.lorax_result_root = config['mock_work_root'] + "/" + "lorax"
        self.mock_isolation = isolation
        self.iso_map = rlvars['iso_map']
        self.cloudimages = rlvars['cloudimages']
        self.release_candidate = rc
        self.s3 = s3
        self.force_unpack = force_unpack
        self.force_download = force_download
        self.extra_iso = extra_iso
        self.extra_iso_mode = extra_iso_mode
        self.checksum = rlvars['checksum']
        self.profile = rlvars['profile']
        self.hashed = hashed
        self.updated_image = updated_image
        self.updated_image_increment = "." + image_increment
        self.updated_image_date = (time.strftime("%Y%m%d", time.localtime())
                                   + self.updated_image_increment)

        # Relevant major version items
        self.arch = arch
        self.arches = rlvars['allowed_arches']
        self.release = rlvars['revision']
        self.minor_version = rlvars['minor']
        self.revision_level = rlvars['revision'] + "-" + rlvars['rclvl']
        self.revision = rlvars['revision']
        self.rclvl = rlvars['rclvl']
        self.repos = rlvars['iso_map']['lorax']['repos']
        self.repo_base_url = config['repo_base_url']
        self.project_id = rlvars['project_id']
        self.structure = rlvars['structure']
        self.bugurl = rlvars['bugurl']

        self.extra_files = rlvars['extra_files']
        self.translators = config['translators']

        self.container = config['container']
        if 'container' in rlvars and len(rlvars['container']) > 0:
            self.container = rlvars['container']

        # all bucket related info
        if s3_region:
            self.s3_region = s3_region
        else:
            self.s3_region = config['aws_region']

        if s3_bucket:
            self.s3_bucket = s3_bucket
        else:
            self.s3_bucket = config['bucket']

        if s3_bucket_url:
            self.s3_bucket_url = s3_bucket_url
        else:
            self.s3_bucket_url = config['bucket_url']

        #if s3:
        #    self.s3 = boto3.client('s3')

        # Templates
        file_loader = FileSystemLoader(f"{_rootdir}/templates")
        self.tmplenv = Environment(loader=file_loader)

        self.compose_latest_dir = os.path.join(
                config['compose_root'],
                major,
                f"latest-{self.shortname}-{self.profile}"
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
                "work/isos"
        )

        self.live_work_dir = os.path.join(
                self.compose_latest_dir,
                "work/live"
        )

        self.image_work_dir = os.path.join(
                self.compose_latest_dir,
                "work/images"
        )

        self.lorax_work_dir = os.path.join(
                self.compose_latest_dir,
                "work/lorax"
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
        self.repolist = Shared.build_repo_list(
                self.repo_base_url,
                self.repos,
                self.project_id,
                self.current_arch,
                self.compose_latest_sync,
                self.compose_dir_is_here,
                self.hashed
        )
        self.log.info(self.revision_level)

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
            self.shortname.lower(), self.major_version, self.current_arch)
        )
        self.log.info('ISO Build completed.')

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

        mock_iso_path = '/var/tmp/lorax-' + self.release + '.cfg'
        mock_sh_path = '/var/tmp/isobuild.sh'
        iso_template_path = '/var/tmp/buildImage.sh'
        required_pkgs = self.iso_map['lorax']['required_pkgs']

        rclevel = ''
        if self.release_candidate:
            rclevel = '-' + self.rclvl

        mock_iso_template_output = mock_iso_template.render(
                arch=self.current_arch,
                major=self.major_version,
                releasever=self.release,
                fullname=self.fullname,
                shortname=self.shortname,
                required_pkgs=required_pkgs,
                dist=self.disttag,
                repos=self.repolist,
                user_agent='{{ user_agent }}',
        )

        mock_sh_template_output = mock_sh_template.render(
                arch=self.current_arch,
                major=self.major_version,
                releasever=self.release,
                isolation=self.mock_isolation,
                builddir=self.mock_work_root,
                shortname=self.shortname,
                revision=self.release,
        )

        iso_template_output = iso_template.render(
                arch=self.current_arch,
                major=self.major_version,
                minor=self.minor_version,
                shortname=self.shortname,
                repos=self.repolist,
                variant=self.iso_map['lorax']['variant'],
                lorax=self.iso_map['lorax']['lorax_removes'],
                distname=self.distname,
                revision=self.release,
                rc=rclevel,
                builddir=self.mock_work_root,
                lorax_work_root=self.lorax_result_root,
                bugurl=self.bugurl,
                squashfs_only=self.iso_map['lorax'].get('squashfs_only', None),
        )

        with open(mock_iso_path, "w+") as mock_iso_entry:
            mock_iso_entry.write(mock_iso_template_output)
            mock_iso_entry.close()

        with open(mock_sh_path, "w+") as mock_sh_entry:
            mock_sh_entry.write(mock_sh_template_output)
            mock_sh_entry.close()

        with open(iso_template_path, "w+") as iso_template_entry:
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

    def run_pull_lorax_artifacts(self):
        """
        Pulls the required artifacts and unpacks it to work/lorax/$arch
        """
        # Determine if we're only managing one architecture out of all of them.
        # It does not hurt to do everything at once. But the option is there.
        unpack_single_arch = False
        arches_to_unpack = self.arches
        if self.arch:
            unpack_single_arch = True
            arches_to_unpack = [self.arch]

        self.log.info(Color.INFO + 'Determining the latest pulls...')
        if self.s3:
            latest_artifacts = Shared.s3_determine_latest(
                    self.s3_bucket,
                    self.release,
                    self.arches,
                    'tar.gz',
                    'lorax',
                    'buildiso',
                    self.translators,
                    self.log
            )
        else:
            latest_artifacts = Shared.reqs_determine_latest(
                    self.s3_bucket_url,
                    self.release,
                    self.arches,
                    'tar.gz',
                    'lorax',
                    self.log
            )

        self.log.info(Color.INFO + 'Downloading requested artifact(s)')
        for arch in arches_to_unpack:
            lorax_arch_dir = os.path.join(
                self.lorax_work_dir,
                arch
            )

            if arch not in latest_artifacts:
                self.log.error(Color.FAIL + 'No lorax artifacts for ' + arch)
                continue

            source_path = latest_artifacts[arch]

            full_drop = f'{lorax_arch_dir}/lorax-{self.release}-{arch}.tar.gz'

            if not os.path.exists(lorax_arch_dir):
                os.makedirs(lorax_arch_dir, exist_ok=True)

            self.log.info(
                    'Downloading artifact for ' + Color.BOLD + arch + Color.END
            )
            if self.s3:
                Shared.s3_download_artifacts(
                        self.force_download,
                        self.s3_bucket,
                        source_path,
                        full_drop,
                        self.log
                )
            else:
                Shared.reqs_download_artifacts(
                        self.force_download,
                        self.s3_bucket_url,
                        source_path,
                        full_drop,
                        self.log
                )
        self.log.info(Color.INFO + 'Download phase completed')
        self.log.info(Color.INFO + 'Beginning unpack phase...')

        for arch in arches_to_unpack:
            tarname = f'lorax-{self.release}-{arch}.tar.gz'

            tarball = os.path.join(
                    self.lorax_work_dir,
                    arch,
                    tarname
            )

            if not os.path.exists(tarball):
                self.log.error(Color.FAIL + 'Artifact does not exist: ' + tarball)
                continue

            self._unpack_artifacts(self.force_unpack, arch, tarball)

        self.log.info(Color.INFO + 'Unpack phase completed')
        self.log.info(Color.INFO + 'Beginning image variant phase')

        for arch in arches_to_unpack:
            self.log.info(
                    'Copying base lorax for ' + Color.BOLD + arch + Color.END
            )
            for variant in self.iso_map['images']:
                self._copy_lorax_to_variant(self.force_unpack, arch, variant)

            self._copy_boot_to_work(self.force_unpack, arch)

        self.log.info(Color.INFO + 'Image variant phase completed')

        self.log.info(Color.INFO + 'Beginning treeinfo phase')

        for arch in arches_to_unpack:
            for variant in self.iso_map['images']:
                self.log.info(
                        'Configuring treeinfo and discinfo for %s%s %s%s' % (Color.BOLD, arch, variant, Color.END)
                )

                self._treeinfo_wrapper(arch, variant)
                # Do a dirsync for non-disc data
                if not self.iso_map['images'][variant]['disc']:
                    self.log.info(
                            'Syncing repo data and images for %s%s%s' % (Color.BOLD, variant, Color.END)
                    )
                    self._copy_nondisc_to_repo(self.force_unpack, arch, variant)

    def _unpack_artifacts(self, force_unpack, arch, tarball):
        """
        Unpack the requested artifacts(s)
        """
        unpack_dir = os.path.join(self.lorax_work_dir, arch)
        if not force_unpack:
            file_check = os.path.join(unpack_dir, 'lorax/.treeinfo')
            if os.path.exists(file_check):
                self.log.warning(Color.WARN + 'Artifact (' + arch + ') already unpacked')
                return

        self.log.info('Unpacking %s' % tarball)
        with tarfile.open(tarball) as t:
            Shared.tar_safe_extractall(t, unpack_dir)
            t.close()

    def _copy_lorax_to_variant(self, force_unpack, arch, image):
        """
        Copy to variants for easy access of mkiso and copying to compose dirs
        """
        src_to_image = os.path.join(
                self.lorax_work_dir,
                arch,
                'lorax'
        )

        iso_to_go = os.path.join(
                self.iso_work_dir,
                arch
        )

        if not os.path.exists(os.path.join(src_to_image, '.treeinfo')):
            self.log.error(Color.FAIL + 'Lorax base image does not exist')
            return

        path_to_image = os.path.join(
                self.lorax_work_dir,
                arch,
                image
        )

        if not force_unpack:
            file_check = os.path.join(path_to_image, '.treeinfo')
            if os.path.exists(file_check):
                self.log.warning(Color.WARN + 'Lorax image for ' + image + ' already exists')
                return

        self.log.info('Copying base lorax to %s directory...' % image)
        try:
            shutil.copytree(src_to_image, path_to_image, copy_function=shutil.copy2, dirs_exist_ok=True)
        except:
            self.log.error('%s already exists??' % image)

        if self.iso_map['images'][image]['disc']:
            self.log.info('Removing boot.iso from %s' % image)
            try:
                os.remove(path_to_image + '/images/boot.iso')
                os.remove(path_to_image + '/images/boot.iso.manifest')
            except:
                self.log.error(
                            '[' + Color.BOLD + Color.YELLOW + 'FAIL' + Color.END + '] ' +
                            'Cannot remove boot.iso'
                )

    def _copy_boot_to_work(self, force_unpack, arch):
        src_to_image = os.path.join(self.lorax_work_dir, arch, 'lorax')
        iso_to_go = os.path.join(self.iso_work_dir, arch)
        path_to_src_image = os.path.join(src_to_image, 'images/boot.iso')

        rclevel = ''
        if self.release_candidate:
            rclevel = '-' + self.rclvl

        discname = f'{self.shortname}-{self.release}{rclevel}-{arch}-boot.iso'

        isobootpath = os.path.join(iso_to_go, discname)
        manifest = f'{isobootpath}.manifest'
        link_name = f'{self.shortname}-{arch}-boot.iso'
        link_manifest = link_name + '.manifest'
        latest_link_name = f'{self.shortname}-{self.major_version}-latest-{arch}-boot.iso'
        latest_link_manifest = latest_link_name + '.manifest'
        isobootpath = os.path.join(iso_to_go, discname)
        linkbootpath = os.path.join(iso_to_go, link_name)
        manifestlink = os.path.join(iso_to_go, link_manifest)
        latestlinkbootpath = os.path.join(iso_to_go, latest_link_name)
        latestmanifestlink = os.path.join(iso_to_go, latest_link_manifest)

        if not force_unpack:
            file_check = isobootpath
            if os.path.exists(file_check):
                self.log.warning(Color.WARN + 'Boot image (' + discname + ') already exists')
                return

        self.log.info('Copying %s boot iso to work directory...' % arch)
        os.makedirs(iso_to_go, exist_ok=True)
        try:
            shutil.copy2(path_to_src_image, isobootpath)

            # For Rocky-ARCH-boot.iso
            if os.path.exists(linkbootpath):
                os.remove(linkbootpath)
            os.symlink(discname, linkbootpath)

            # For Rocky-X-latest-ARCH-boot.iso
            if os.path.exists(latestlinkbootpath):
                os.remove(latestlinkbootpath)
            os.symlink(discname, latestlinkbootpath)
        except Exception as e:
            self.log.error(Color.FAIL + 'We could not copy the image or create a symlink.')
            raise SystemExit(e)

        # For Rocky-ARCH-boot.iso
        if os.path.exists(path_to_src_image + '.manifest'):
            shutil.copy2(path_to_src_image + '.manifest', manifest)
            os.symlink(manifest.split('/')[-1], manifestlink)
            os.symlink(manifest.split('/')[-1], latestmanifestlink)

        self.log.info('Creating checksum for %s boot iso...' % arch)
        checksum = Shared.get_checksum(isobootpath, self.checksum, self.log)
        if not checksum:
            self.log.error(Color.FAIL + isobootpath + ' not found! Are you sure we copied it?')
            return
        with open(isobootpath + '.CHECKSUM', "w+") as c:
            c.write(checksum)
            c.close()

        # For Rocky-ARCH-boot.iso
        linksum = Shared.get_checksum(linkbootpath, self.checksum, self.log)
        if not linksum:
            self.log.error(Color.FAIL + linkbootpath + ' not found! Did we actually make the symlink?')
            return
        with open(linkbootpath + '.CHECKSUM', "w+") as l:
            l.write(linksum)
            l.close()

        # For Rocky-X-latest-ARCH-boot.iso
        latestlinksum = Shared.get_checksum(latestlinkbootpath, self.checksum, self.log)
        if not latestlinksum:
            self.log.error(Color.FAIL + latestlinkbootpath + ' not found! Did we actually make the symlink?')
            return
        with open(latestlinkbootpath + '.CHECKSUM', "w+") as l:
            l.write(latestlinksum)
            l.close()

    def _copy_nondisc_to_repo(self, force_unpack, arch, repo):
        """
        Syncs data from a non-disc set of images to the appropriate repo. Repo
        and image MUST match names for this to work.
        """
        pathway = os.path.join(
                self.compose_latest_sync,
                repo,
                arch,
                'os'
        )

        kspathway = os.path.join(
                self.compose_latest_sync,
                repo,
                arch,
                'kickstart'
        )

        src_to_image = os.path.join(
                self.lorax_work_dir,
                arch,
                repo
        )

        if not os.path.exists(pathway):
            self.log.error(Color.FAIL +
                    'Repo and Image variant either does NOT match or does ' +
                    'NOT exist. Are you sure you have synced the repository?'
            )

        if not force_unpack:
            found_files = []
            for y in ArchCheck.archfile[arch]:
                imgpath = os.path.join(
                        pathway,
                        y
                )
                if os.path.exists(imgpath):
                    found_files.append(y)

            if os.path.exists(pathway + '/images/boot.iso'):
                found_files.append('/images/boot.iso')

            if len(found_files) > 0:
                self.log.warning(Color.WARN + 'Images and data for ' + repo + ' and ' + arch + ' already exists.')
                return

        self.log.info(Color.INFO + 'Copying images and data for ' + repo + ' ' + arch)

        try:
            shutil.copytree(src_to_image, pathway, copy_function=shutil.copy2, dirs_exist_ok=True)
            shutil.copytree(src_to_image, kspathway, copy_function=shutil.copy2, dirs_exist_ok=True)
        except:
            self.log.error('%s already exists??' % repo)


    def run_boot_sync(self):
        """
        This unpacks into BaseOS/$arch/os, assuming there's no data actually
        there. There should be checks.

        1. Sync from work/lorax/$arch to work/lorax/$arch/dvd
        2. Sync from work/lorax/$arch to work/lorax/$arch/minimal
        3. Sync from work/lorax/$arch to BaseOS/$arch/os
        4. Modify (3) .treeinfo
        5. Modify (1) .treeinfo, keep out boot.iso checksum
        6. Create a .treeinfo for AppStream
        """
        unpack_single_arch = False
        arches_to_unpack = self.arches
        if self.arch:
            unpack_single_arch = True
            arches_to_unpack = [self.arch]

        self._sync_boot(force_unpack=self.force_unpack, arch=self.arch, image=None)
        #self._treeinfo_write(arch=self.arch)

    def _sync_boot(self, force_unpack, arch, image):
        """
        Syncs whatever
        """
        self.log.info('Copying lorax to %s directory...' % image)
        # checks here, report that it already exists

    def _treeinfo_wrapper(self, arch, variant):
        """
        Ensure treeinfo and discinfo is written correctly based on the variant
        passed. Each file should be configured similarly but also differently
        from the next. The Shared module does have a .treeinfo writer, but it
        is for basic use. Eventually it'll be expanded to handle this scenario.
        """
        image = os.path.join(self.lorax_work_dir, arch, variant)
        imagemap = self.iso_map['images'][variant]
        data = {
                'arch': arch,
                'variant': variant,
                'variant_path': image,
                'checksum': self.checksum,
                'distname': self.distname,
                'fullname': self.fullname,
                'shortname': self.shortname,
                'release': self.release,
                'timestamp': self.timestamp,
        }

        try:
            Shared.treeinfo_modify_write(data, imagemap, self.log)
        except Exception as e:
            self.log.error(Color.FAIL + 'There was an error writing treeinfo.')
            self.log.error(e)

    # Next set of functions are loosely borrowed (in concept) from pungi. Some
    # stuff may be combined/mixed together, other things may be simplified or
    # reduced in nature.
    def run_build_extra_iso(self):
        """
        Builds DVD images based on the data created from the initial lorax on
        each arch. This should NOT be called during the usual run() section.
        """
        sync_root = self.compose_latest_sync

        self.log.info(Color.INFO + 'Starting Extra ISOs phase')

        if not os.path.exists(self.compose_base):
            self.log.info(Color.FAIL + 'The compose directory MUST be here. Cannot continue.')
            raise SystemExit()

        self._extra_iso_build_wrap()

        self.log.info('Compose repo directory: %s' % sync_root)
        self.log.info('ISO result directory: %s/$arch' % self.iso_work_dir)
        self.log.info(Color.INFO + 'Extra ISO phase completed.')

    def _extra_iso_build_wrap(self):
        """
        Try to figure out where the build is going, podman or mock.
        """
        work_root = os.path.join(
                self.compose_latest_dir,
                'work'
        )

        arches_to_build = self.arches
        if self.arch:
            arches_to_build = [self.arch]

        images_to_build = list(self.iso_map['images'].keys())
        if self.extra_iso:
            images_to_build = [self.extra_iso]

        images_to_skip = []

        for y in images_to_build:
            if 'isoskip' in self.iso_map['images'][y] and self.iso_map['images'][y]['isoskip']:
                self.log.info(Color.WARN + f'Skipping {y} image')
                images_to_skip.append(y)
                continue

            reposcan = True
            if 'reposcan' in self.iso_map['images'][y] and not self.iso_map['images'][y]['reposcan']:
                self.log.info(Color.WARN + f"Skipping compose repository scans for {y}")
                reposcan = False

            # Kind of hacky, but if we decide to have more than boot/dvd iso's,
            # we need to make sure volname matches the initial lorax image,
            # which the volid contains "dvd". AKA, file name doesn't always
            # equate to volume ID
            if 'volname' in self.iso_map['images'][y]:
                volname = self.iso_map['images'][y]['volname']
            else:
                volname = y

            for a in arches_to_build:
                lorax_path = os.path.join(self.lorax_work_dir, a, 'lorax', '.treeinfo')
                image_path = os.path.join(self.lorax_work_dir, a, y, '.treeinfo')
                if not os.path.exists(image_path):
                    self.log.error(Color.FAIL + 'Lorax data not found for ' + y + '. Skipping.')

                    if not os.path.exists(lorax_path):
                        self.log.error(Color.FAIL + 'Lorax not found at all. This is considered fatal.')

                    raise SystemExit()

                grafts = self._generate_graft_points(
                        a,
                        y,
                        self.iso_map['images'][y]['repos'],
                        reposcan=reposcan
                )
                self._extra_iso_local_config(a, y, grafts, work_root, volname)

                if self.extra_iso_mode == 'local':
                    self._extra_iso_local_run(a, y, work_root)
                elif self.extra_iso_mode == 'podman':
                    continue
                else:
                    self.log.error(Color.FAIL + 'Mode specified is not valid.')
                    raise SystemExit()

        if self.extra_iso_mode == 'podman':
            # I can't think of a better way to do this
            images_to_build_podman = images_to_build.copy()
            for item in images_to_build_podman[:]:
                for skip in images_to_skip:
                    if item == skip:
                        images_to_build_podman.remove(item)

            self._extra_iso_podman_run(arches_to_build, images_to_build_podman, work_root)

    def _extra_iso_local_config(self, arch, image, grafts, work_root, volname):
        """
        Local ISO build configuration - This generates the configuration for
        both mock and podman entries
        """
        self.log.info('Generating Extra ISO configuration and script')

        entries_dir = os.path.join(work_root, "entries")
        boot_iso = os.path.join(work_root, "lorax", arch, "lorax/images/boot.iso")
        mock_iso_template = self.tmplenv.get_template('isomock.tmpl.cfg')
        mock_sh_template = self.tmplenv.get_template('extraisobuild.tmpl.sh')
        iso_template = self.tmplenv.get_template('buildExtraImage.tmpl.sh')
        xorriso_template = self.tmplenv.get_template('xorriso.tmpl.txt')
        iso_readme_template = self.tmplenv.get_template('ISOREADME.tmpl')

        mock_iso_path = f'/var/tmp/lorax-{self.major_version}.cfg'
        mock_sh_path = f'{entries_dir}/extraisobuild-{arch}-{image}.sh'
        iso_template_path = f'{entries_dir}/buildExtraImage-{arch}-{image}.sh'
        xorriso_template_path = f'{entries_dir}/xorriso-{arch}-{image}.txt'
        iso_readme_path = f'{self.iso_work_dir}/{arch}/README'
        #print(iso_readme_path)

        log_root = os.path.join(
                work_root,
                "logs",
                self.date_stamp
        )

        if not os.path.exists(log_root):
            os.makedirs(log_root, exist_ok=True)

        log_path_command = f'| tee -a {log_root}/{arch}-{image}.log'

        rclevel = ''
        if self.release_candidate:
            rclevel = '-' + self.rclvl

        datestamp = ''
        if self.updated_image:
            datestamp = '-' + self.updated_image_date

        volid = f'{self.shortname}-{self.major_version}-{self.minor_version}{rclevel}-{arch}-{volname}'
        isoname = f'{self.shortname}-{self.release}{rclevel}{datestamp}-{arch}-{image}.iso'
        generic_isoname = f'{self.shortname}-{arch}-{image}.iso'
        latest_isoname = f'{self.shortname}-{self.major_version}-latest-{arch}-{image}.iso'
        required_pkgs = self.iso_map['lorax']['required_pkgs']

        lorax_pkg_cmd = '/usr/bin/dnf install {} -y {}'.format(
                ' '.join(required_pkgs),
                log_path_command
        )

        mock_iso_template_output = mock_iso_template.render(
                arch=self.current_arch,
                major=self.major_version,
                fullname=self.fullname,
                shortname=self.shortname,
                required_pkgs=required_pkgs,
                dist=self.disttag,
                repos=self.repolist,
                user_agent='{{ user_agent }}',
                compose_dir_is_here=True,
                compose_dir=self.compose_root,
        )

        mock_sh_template_output = mock_sh_template.render(
                arch=self.current_arch,
                major=self.major_version,
                isolation=self.mock_isolation,
                builddir=self.mock_work_root,
                shortname=self.shortname,
                isoname=isoname,
                entries_dir=entries_dir,
                image=image,
        )

        opts = {
                'arch': arch,
                'iso_name': isoname,
                'volid': volid,
                'graft_points': grafts,
                'iso_level': self.iso_map['iso_level'],
        }

        # Generate a xorriso compatible dialog
        with open(grafts) as xp:
            xorpoint = xp.read()
            xp.close()
        xorriso_template_output = xorriso_template.render(
                boot_iso=boot_iso,
                isoname=isoname,
                volid=volid,
                graft=xorpoint,
                arch=arch,
        )
        with open(xorriso_template_path, "w+") as xorriso_template_entry:
            xorriso_template_entry.write(xorriso_template_output)
            xorriso_template_entry.close()
        opts['graft_points'] = xorriso_template_path

        make_image = '{} {}'.format(
                Shared.get_make_image_cmd(opts),
                log_path_command
        )
        implantmd5 = Shared.get_implantisomd5_cmd(opts)
        make_manifest = Shared.get_manifest_cmd(opts)

        iso_template_output = iso_template.render(
                extra_iso_mode=self.extra_iso_mode,
                arch=arch,
                compose_work_iso_dir=self.iso_work_dir,
                make_image=make_image,
                implantmd5=implantmd5,
                make_manifest=make_manifest,
                lorax_pkg_cmd=lorax_pkg_cmd,
                isoname=isoname,
                generic_isoname=generic_isoname,
                latest_isoname=latest_isoname,
        )

        iso_readme_template_output = iso_readme_template.render(
                arch=arch
        )

        with open(mock_iso_path, "w+") as mock_iso_entry:
            mock_iso_entry.write(mock_iso_template_output)
            mock_iso_entry.close()

        with open(mock_sh_path, "w+") as mock_sh_entry:
            mock_sh_entry.write(mock_sh_template_output)
            mock_sh_entry.close()

        with open(iso_template_path, "w+") as iso_template_entry:
            iso_template_entry.write(iso_template_output)
            iso_template_entry.close()

        with open(iso_readme_path, "w+") as iso_readme_entry:
            iso_readme_entry.write(iso_readme_template_output)
            iso_readme_entry.close()

        os.chmod(mock_sh_path, 0o755)
        os.chmod(iso_template_path, 0o755)

    def _extra_iso_local_run(self, arch, image, work_root):
        """
        Runs the actual local process using mock. This is for running in
        peridot or running on a machine that does not have podman, but does
        have mock available.
        """
        entries_dir = os.path.join(work_root, "entries")
        extra_iso_cmd = f'/bin/bash {entries_dir}/extraisobuild-{arch}-{image}.sh'
        self.log.info('Starting mock build...')
        p = subprocess.call(shlex.split(extra_iso_cmd))
        if p != 0:
            self.log.error('An error occured during execution.')
            self.log.error('See the logs for more information.')
            raise SystemExit()
        # Copy it if the compose dir is here?

    def _extra_iso_podman_run(self, arches, images, work_root):
        """
        Does all the image building in podman containers to parallelize the
        builds. This is a case where you can call this instead of looping mock,
        or not run it in peridot. This gives the Release Engineer a little more
        flexibility if they care enough.

        This honestly assumes you are running this on a machine that has access
        to the compose directories. It's the same as if you were doing a
        reposync of the repositories.
        """
        cmd = Shared.podman_cmd(self.log)
        entries_dir = os.path.join(work_root, "entries")
        isos_dir = os.path.join(work_root, "isos")
        bad_exit_list = []
        checksum_list = []

        datestamp = ''
        if self.updated_image:
            datestamp = '-' + self.updated_image_date

        for i in images:
            entry_name_list = []
            image_name = i
            arch_sync = arches.copy()

            for a in arch_sync:
                entry_name = f'buildExtraImage-{a}-{i}.sh'
                entry_name_list.append(entry_name)

                rclevel = ''
                if self.release_candidate:
                    rclevel = '-' + self.rclvl

                isoname = '{}/{}-{}{}{}-{}-{}.iso'.format(
                        a,
                        self.shortname,
                        self.revision,
                        rclevel,
                        datestamp,
                        a,
                        i
                )

                genericname = '{}/{}-{}-{}.iso'.format(
                        a,
                        self.shortname,
                        a,
                        i
                )

                latestname = '{}/{}-{}-latest-{}-{}.iso'.format(
                        a,
                        self.shortname,
                        self.major_version,
                        a,
                        i
                )

                checksum_list.append(isoname)
                checksum_list.append(genericname)
                checksum_list.append(latestname)

            for pod in entry_name_list:
                podman_cmd_entry = '{} run -d -it -v "{}:{}" -v "{}:{}" --name {} --entrypoint {}/{} {}'.format(
                        cmd,
                        self.compose_root,
                        self.compose_root,
                        entries_dir,
                        entries_dir,
                        pod,
                        entries_dir,
                        pod,
                        self.container
                )

                process = subprocess.call(
                        shlex.split(podman_cmd_entry),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                )

            join_all_pods = ' '.join(entry_name_list)
            time.sleep(3)
            self.log.info(Color.INFO + 'Building ' + i + ' ...')
            pod_watcher = f'{cmd} wait {join_all_pods}'

            watch_man = subprocess.call(
                    shlex.split(pod_watcher),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
            )

            # After the above is done, we'll check each pod process for an exit
            # code.
            pattern = "Exited (0)"
            for pod in entry_name_list:
                checkcmd = f'{cmd} ps -f status=exited -f name={pod}'
                podcheck = subprocess.Popen(
                        checkcmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True
                )

                output, errors = podcheck.communicate()
                if 'Exited (0)' not in output.decode():
                    self.log.error(Color.FAIL + pod)
                    bad_exit_list.append(pod)

            rmcmd = f'{cmd} rm {join_all_pods}'

            rmpod = subprocess.Popen(
                    rmcmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=True
            )

            entry_name_list.clear()
            for p in checksum_list:
                path = os.path.join(isos_dir, p)
                if os.path.exists(path):
                    self.log.info(Color.INFO + 'Performing checksum for ' + p)
                    checksum = Shared.get_checksum(path, self.checksum, self.log)
                    if not checksum:
                        self.log.error(Color.FAIL + path + ' not found! Are you sure it was built?')
                    with open(path + '.CHECKSUM', "w+") as c:
                        c.write(checksum)
                        c.close()

            self.log.info(Color.INFO + 'Building ' + i + ' completed')

            if len(bad_exit_list) == 0:
                self.log.info(Color.INFO + 'Images built successfully.')
            else:
                self.log.error(
                        Color.FAIL +
                        'There were issues with the work done. As a result, ' +
                        'some/all ISOs may not exist.'
                )


    def _generate_graft_points(
            self,
            arch,
            iso,
            variants,
            reposcan: bool = True,
        ):
        """
        Get a list of packages for an extras ISO. This should NOT be called
        during the usual run() section.
        """
        lorax_base_dir = os.path.join(self.lorax_work_dir, arch)
        global_work_dir = os.path.join(self.compose_latest_dir, "work/global")

        self.log.info(Color.INFO + 'Generating graft points for extra iso: (' + arch + ') ' + iso)
        files = {}
        # This is the data we need to actually boot
        lorax_for_var = os.path.join(lorax_base_dir, iso)

        if not os.path.exists(lorax_for_var + '/.treeinfo'):
            self.log.info(
                    Color.FAIL +
                    '!! .treeinfo is missing, does this variant actually exist? !!'
            )
            return

        # extra files
        extra_files_for_var = os.path.join(
            global_work_dir,
            "extra-files"
        )

        # actually get the boot data
        files = self._get_grafts([lorax_for_var, extra_files_for_var])

        # Some variants cannot go through a proper scan.
        if reposcan:
            # This is to get all the packages for each repo
            for repo in variants:
                pkg_for_var = os.path.join(
                        self.compose_latest_sync,
                        repo,
                        arch,
                        self.structure['packages']
                )
                rd_for_var = os.path.join(
                        self.compose_latest_sync,
                        repo,
                        arch,
                        self.structure['repodata']
                )

                for k, v in self._get_grafts([pkg_for_var]).items():
                    files[os.path.join(repo, "Packages", k)] = v

                for k, v in self._get_grafts([rd_for_var]).items():
                    files[os.path.join(repo, "repodata", k)] = v

        grafts = f'{lorax_base_dir}/{iso}-{arch}-grafts'

        xorrs = f'{lorax_base_dir}/xorriso-{iso}-{arch}.txt'

        # Generate exclusion list/dict from boot.iso manifest
        boot_manifest = f'{lorax_base_dir}/lorax/images/boot.iso.manifest'
        # Boot configs and images that may change
        # It's unlikely these will be changed in empanadas, they're used as is
        # and it works fine. This is a carry over from a recent pungi commit,
        # based on an issue I had filed. The above was the original part, the
        # below is a pungi "buildinstall" thing that we don't do, but may
        # include as a feature if it ever happens.
        updatable_files = set(ArchCheck.boot_configs + ArchCheck.boot_images + ['.discinfo'])
        ignores = set()
        updatables = set()

        try:
            with open(boot_manifest) as i:
        #        ignores = set(line.lstrip("/").rstrip("\n") for line in i)
                for line in i:
                    path = line.lstrip("/").rstrip("\n")
                    if path in updatable_files:
                        updatables.add(path)
                    else:
                        ignores.add(path)
        except Exception as e:
            self.log.error(Color.FAIL + 'File was likely not found.')
            raise SystemExit(e)

        self._write_grafts(
                grafts,
                xorrs,
                files,
                exclude=ignores,
                update=updatables
        )

        grafters = xorrs
        return grafters

    def _get_grafts(self, paths, exclusive_paths=None, exclude=None):
        """
        Actually get some grafts (get_iso_contents), called by generate grafts
        """
        result = {}
        exclude = exclude or []
        exclusive_paths = exclusive_paths or []

        for p in paths:
            if isinstance(p, dict):
                tree = p
            else:
                tree = Idents.scanning(p)
            result = Idents.merging(result, tree)

        for p in exclusive_paths:
            tree = Idents.scanning(p)
            result = Idents.merging(result, tree, exclusive=True)

        # Resolves possible symlinks
        for key in result.keys():
            path = result[key]
            if os.path.islink(path):
                real_path = os.readlink(path)
                abspath = os.path.normpath(os.path.join(os.path.dirname(path), real_path))
                if not abspath.startswith(self.compose_base):
                    result[key] = abspath

        return result

    def _write_grafts(self, filepath, xorrspath, u, exclude=None, update=None):
        """
        Write out the graft points
        """
        seen = set()
        # There are files that are on the exclude list typically.
        exclude = exclude or []
        # There is a chance files may get updated before being placed in a
        # variant ISO - it's rare though. most that will be different is
        # .discinfo
        update = update or []
        result = {}
        for zl in sorted(u, reverse=True):
            dirn = os.path.dirname(zl)

            if not zl.endswith("/"):
                result[zl] = u[zl]
                seen.add(dirn)
                continue

            found = False
            for j in seen:
                if j.startswith(dirn):
                    found = True
                    break
            if not found:
                result[zl] = u[zl]
            seen.add(dirn)

        # We check first if a file needs to be updated first before relying on
        # the boot.iso manifest to exclude a file
        with open(xorrspath, "w") as fx:
            for zm in sorted(result, key=Idents.sorting):
                found = False
                replace = False
                for upda in update:
                    if fnmatch(zm, upda):
                        #print(f'updating: {zm} {upda}')
                        replace = True
                        break
                for excl in exclude:
                    if fnmatch(zm, excl):
                        #print(f'ignoring: {zm} {excl}')
                        found = True
                        break
                if found:
                    continue
                mcmd = "-update" if replace else "-map"
                fx.write("%s %s %s\n" % (mcmd, u[zm], zm))
            fx.close()

    def run_pull_iso_images(self):
        """
        Pulls ISO's made in v2
        """
        arches_to_unpack = self.arches
        latest_artifacts = {}
        if self.arch:
            unpack_single_arch = True
            arches_to_unpack = [self.arch]

        print("not supported")
        sys.exit(1)

    def run_pull_generic_images(self):
        """
        Pulls generic images built in peridot and places them where they need
        to be. This relies on a list called "cloudimages" in the version
        configuration.
        """
        unpack_single_arch = False
        arches_to_unpack = self.arches
        latest_artifacts = {}
        if self.arch:
            unpack_single_arch = True
            arches_to_unpack = [self.arch]

        for name, extra in self.cloudimages['images'].items():
            self.log.info(Color.INFO + 'Determining the latest images for ' + name + ' ...')
            formattype = extra['format']
            latest_artifacts[name] = {}
            primary_variant = extra['primary_variant'] if 'primary_variant' in extra else None
            latest_artifacts[name]['primary'] = primary_variant
            latest_artifacts[name]['formattype'] = formattype

            variants = extra['variants'] if 'variants' in extra.keys() else [None] # need to loop once
            imagename = name
            variantname = name

            for variant in variants:
                if variant:
                    variantname = f"{name}-{variant}"
                    self.log.info(Color.INFO + 'Getting latest for variant ' + variant + ' ...')
                if self.s3:
                    latest_artifacts[name][variantname] = Shared.s3_determine_latest(
                            self.s3_bucket,
                            self.release,
                            arches_to_unpack,
                            formattype,
                            variantname,
                            'buildimage',
                            self.translators,
                            self.log
                    )

                else:
                    latest_artifacts[name][variantname] = Shared.reqs_determine_latest(
                            self.s3_bucket_url,
                            self.release,
                            arches_to_unpack,
                            formattype,
                            variantname,
                            self.log
                    )

                # latest_artifacts should have at least 1 result if has_variants, else == 1
                if not len(latest_artifacts[name][variantname]) > 0:
                    self.log.warning(Color.WARN + 'No images found for ' + variantname +
                            '. This means it will be skipped.')

            del imagename
            del variantname
            del variants

        #print(latest_artifacts)
        for keyname in latest_artifacts.keys():
            primary = latest_artifacts[keyname]['primary']
            filetype = latest_artifacts[keyname]['formattype']
            for imgname in latest_artifacts[keyname]:
                keysect = latest_artifacts[keyname][imgname]
                if imgname == 'primary':
                    continue

                if not keysect:
                    continue

                if type(keysect) == str:
                    continue

                self.log.info(Color.INFO + 'Attempting to download requested ' +
                              'artifacts (' + keyname + ')')

                for arch in arches_to_unpack:
                    image_arch_dir = os.path.join(
                            self.image_work_dir,
                            arch
                    )

                    if arch not in keysect:
                        self.log.warning(Color.WARN + 'This architecture (' + arch + ') does not exist for this image orvar is a string.')
                        continue

                    source_path = keysect[arch]
                    drop_name = source_path.split('/')[-1]

                    # Docker containers get a "layer" name, this hack gets
                    # around it. I didn't feel like adding another config opt.
                    if 'layer' in drop_name:
                        fsuffix = drop_name.replace('layer', '')
                        drop_name = source_path.split('/')[-3] + fsuffix

                    checksum_name = drop_name + '.CHECKSUM'
                    full_drop = f'{image_arch_dir}/{drop_name}'

                    checksum_drop = f'{image_arch_dir}/{drop_name}.CHECKSUM'

                    if not os.path.exists(image_arch_dir):
                        os.makedirs(image_arch_dir, exist_ok=True)

                    self.log.info('Downloading artifact for ' + Color.BOLD + arch + Color.END)
                    if self.s3:
                        Shared.s3_download_artifacts(
                                self.force_download,
                                self.s3_bucket,
                                source_path,
                                full_drop,
                                self.log
                        )
                    else:
                        Shared.reqs_download_artifacts(
                                self.force_download,
                                self.s3_bucket_url,
                                source_path,
                                full_drop,
                                self.log
                        )

                    self.log.info('Creating checksum ...')
                    checksum = Shared.get_checksum(full_drop, self.checksum, self.log)
                    if not checksum:
                        self.log.error(Color.FAIL + full_drop + ' not found! Are you sure we copied it?')
                        continue
                    with open(checksum_drop, 'w+') as c:
                        c.write(checksum)
                        c.close()

                    self.log.info('Creating a symlink to latest image...')
                    latest_name = '{}/{}-{}-{}.latest.{}.{}'.format(
                            image_arch_dir,
                            self.shortname,
                            self.major_version,
                            imgname,
                            arch,
                            filetype
                    )
                    latest_path = latest_name.split('/')[-1]
                    latest_checksum = '{}/{}-{}-{}.latest.{}.{}.CHECKSUM'.format(
                            image_arch_dir,
                            self.shortname,
                            self.major_version,
                            imgname,
                            arch,
                            filetype
                    )
                    # For some reason python doesn't have a "yeah just change this
                    # link" part of the function
                    if os.path.exists(latest_name):
                        os.remove(latest_name)

                    os.symlink(drop_name, latest_name)

                    self.log.info('Creating checksum for latest symlinked image...')
                    shutil.copy2(checksum_drop, latest_checksum)
                    with open(latest_checksum, 'r') as link:
                        checkdata = link.read()

                    checkdata = checkdata.replace(drop_name, latest_path)

                    with open(latest_checksum, 'w+') as link:
                        link.write(checkdata)
                        link.close()

                    # If this is the primary image, set the appropriate symlink
                    # and checksum
                    if primary and primary in drop_name:
                        # If an image is the primary, we set this.
                        latest_primary_name = '{}/{}-{}-{}.latest.{}.{}'.format(
                                image_arch_dir,
                                self.shortname,
                                self.major_version,
                                keyname,
                                arch,
                                filetype
                        )
                        latest_primary_checksum = '{}/{}-{}-{}.latest.{}.{}.CHECKSUM'.format(
                                image_arch_dir,
                                self.shortname,
                                self.major_version,
                                keyname,
                                arch,
                                filetype
                        )
                        latest_primary_path = latest_primary_name.split('/')[-1]

                        self.log.info('This is the primary image, setting link and checksum')
                        if os.path.exists(latest_primary_name):
                            os.remove(latest_primary_name)
                        os.symlink(drop_name, latest_primary_name)
                        shutil.copy2(checksum_drop, latest_primary_checksum)
                        with open(latest_primary_checksum) as link:
                            checkpdata = link.read()
                        checkpdata = checkpdata.replace(drop_name, latest_primary_path)
                        with open(latest_primary_checksum, 'w+') as link:
                            link.write(checkpdata)
                            link.close()

        self.log.info(Color.INFO + 'Image download phase completed')


class LiveBuild:
    """
    This helps us build the live images for Rocky Linux. The mode is "simple"
    by default when using mock.
    """
    def __init__(
            self,
            rlvars,
            config,
            major,
            force_download: bool = False,
            isolation: str = 'simple',
            live_iso_mode: str = 'local',
            compose_dir_is_here: bool = False,
            hashed: bool = False,
            image=None,
            justcopyit: bool = False,
            force_build: bool = False,
            updated_image: bool = False,
            image_increment: str = '0',
            peridot: bool = False,
            builder: str = 'default',
            logger=None
    ):

        self.image = image
        self.justcopyit = justcopyit
        self.fullname = rlvars['fullname']
        self.distname = config['distname']
        self.shortname = config['shortname']
        self.current_arch = config['arch']
        # Relevant config items
        self.major_version = major
        self.compose_dir_is_here = compose_dir_is_here
        self.date_stamp = config['date_stamp']
        self.compose_root = config['compose_root']
        self.compose_base = config['compose_root'] + "/" + major
        self.current_arch = config['arch']
        self.livemap = rlvars['livemap']
        #self.required_pkgs = rlvars['livemap']['required_pkgs']
        self.mock_work_root = config['mock_work_root']
        self.live_result_root = config['mock_work_root'] + "/lmc"
        self.mock_isolation = isolation
        self.force_download = force_download
        self.force_build = force_build
        self.live_iso_mode = live_iso_mode
        self.checksum = rlvars['checksum']
        self.profile = rlvars['profile']
        self.hashed = hashed
        self.peridot = peridot

        # determine builder to use. if a config doesn't have it set, assume
        # lorax, the default option.
        if rlvars['livemap']['builder']:
            self.livebuilder = rlvars['livemap']['builder']
        else:
            self.livebuilder = "lorax"

        if builder == "default":
            self.livebuilder = builder

        # Relevant major version items
        self.arch = config['arch']
        self.arches = rlvars['allowed_arches']
        self.release = rlvars['revision']
        self.minor_version = rlvars['minor']
        self.revision = rlvars['revision'] + "-" + rlvars['rclvl']
        self.rclvl = rlvars['rclvl']
        self.disttag = rlvars['disttag']
        self.repos = rlvars['iso_map']['lorax']['repos']
        self.repo_base_url = config['repo_base_url']
        self.project_id = rlvars['project_id']
        self.structure = rlvars['structure']
        self.bugurl = rlvars['bugurl']

        self.container = config['container']
        if 'container' in rlvars and len(rlvars['container']) > 0:
            self.container = rlvars['container']

        self.updated_image = updated_image
        self.updated_image_increment = "." + image_increment
        self.date = (time.strftime("%Y%m%d", time.localtime())
                                   + self.updated_image_increment)

        # Templates
        file_loader = FileSystemLoader(f"{_rootdir}/templates")
        self.tmplenv = Environment(loader=file_loader)

        self.compose_latest_dir = os.path.join(
                config['compose_root'],
                major,
                f"latest-{self.shortname}-{self.profile}"
        )

        self.compose_latest_sync = os.path.join(
                self.compose_latest_dir,
                "compose"
        )

        self.compose_log_dir = os.path.join(
                self.compose_latest_dir,
                "work/logs"
        )

        self.live_work_dir = os.path.join(
                self.compose_latest_dir,
                "work/live"
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

        self.log.info('live build init')
        self.repolist = Shared.build_repo_list(
                self.repo_base_url,
                self.repos,
                self.project_id,
                self.current_arch,
                self.compose_latest_sync,
                self.compose_dir_is_here,
                self.hashed
        )
        self.log.info(self.revision)

        if not os.path.exists(self.compose_latest_dir):
            self.log.warning(Color.WARN + 'A compose directory was not found ' +
                    'here. If there is a failure, it may be due to it ' +
                    'missing. You may want to generate a fake compose if ' +
                    'you are simply making your own live images and you run ' +
                    'into any errors beyond this point.'
            )

    def run_build_live_iso(self):
        """
        Builds live images based on the data provided at init.
        """
        sync_root = self.compose_latest_sync

        self.log.info(Color.INFO + 'Starting Live ISOs phase')

        # Check that the arch we're assigned is valid...
        if self.current_arch not in self.livemap['allowed_arches']:
            self.log.error(Color.FAIL + 'Running an unsupported architecture.')
            raise SystemExit()

        if self.image not in self.livemap['ksentry'].keys():
            self.log.error(Color.FAIL + 'Trying to build an unknown live image type.')
            raise SystemExit()

        # Check that the builder is lorax, we don't support anything else yet
        if self.livebuilder != "lorax":
            self.log.error(Color.FAIL + 'Attempting to use an unsupported builder.')
            raise SystemExit()

        self._live_iso_build_wrap()

        self.log.info('Compose repo directory: %s' % sync_root)
        self.log.info('Live ISO result directory: %s/$arch' % self.live_work_dir)
        self.log.info(Color.INFO + 'Live ISO phase completed.')

    def _live_iso_build_wrap(self):
        """
        Prepare and actually build the live images. Based on arguments in self,
        we'll either do it on mock in a loop or in podman, just like with the
        extra iso phase.
        """
        work_root = os.path.join(
                self.compose_latest_dir,
                'work'
        )

        images_to_build = list(self.livemap['ksentry'].keys())
        if self.image:
            images_to_build = [self.image]

        self.log.info(
                Color.INFO + 'We are planning to build: ' +
                ', '.join(images_to_build)
        )

        for i in images_to_build:
            self._live_iso_local_config(i, work_root)

            if self.live_iso_mode == 'local':
                self._live_iso_local_run(self.current_arch, i, work_root)
            elif self.live_iso_mode == 'podman':
                continue
            else:
                self.log.error(Color.FAIL + 'Mode specified is not valid.')
                raise SystemExit()

        if self.live_iso_mode == 'podman':
            #self._live_iso_podman_run(self.current_arch, images_to_build, work_root)
            self.log.error(Color.FAIL + 'At this time, live images cannot be ' +
                    'built in podman.')
            raise SystemExit()

    def _live_iso_local_config(self, image, work_root):
        """
        Live ISO build configuration - This generates both mock and podman
        entries, regardless of which one is being used.
        """
        self.log.info('Generating Live ISO configuration and script')

        entries_dir = os.path.join(work_root, "entries")
        mock_iso_template = self.tmplenv.get_template('isomock.tmpl.cfg')
        mock_sh_template = self.tmplenv.get_template('liveisobuild.tmpl.sh')
        iso_template = self.tmplenv.get_template('buildLiveImage.tmpl.sh')
        kloc = 'stage'
        if self.peridot:
            kloc = 'peridot'

        mock_iso_path = f'/var/tmp/live-{self.release}.cfg'
        mock_sh_path = f'{entries_dir}/liveisobuild-{self.current_arch}-{image}.sh'
        iso_template_path = f'{entries_dir}/buildLiveImage-{self.current_arch}-{image}.sh'

        log_root = os.path.join(
                work_root,
                "logs",
                self.date_stamp
        )

        ks_start = self.livemap['ksentry'][image]

        if not os.path.exists(log_root):
            os.makedirs(log_root, exist_ok=True)

        log_path_command = f'| tee -a {log_root}/{self.current_arch}-{image}.log'
        required_pkgs = self.livemap['required_pkgs']

        volid = f'{self.shortname}-{self.release}-{image}'

        isoname = f'{self.shortname}-{self.release}-{image}-{self.current_arch}-{self.date}.iso'

        live_pkg_cmd = '/usr/bin/dnf install {} -y {}'.format(
                ' '.join(required_pkgs),
                log_path_command
        )

        git_clone_cmd = '/usr/bin/git clone {} -b {} /builddir/ks {}'.format(
                self.livemap['git_repo'],
                self.livemap['branch'],
                log_path_command
        )

        make_image_cmd = ('/usr/sbin/livemedia-creator --ks {} --no-virt '
                '--resultdir /builddir/lmc --project="{} {}" --make-iso --volid {} '
                '--iso-only --iso-name {} --releasever={} --nomacboot {}').format(
                        '/builddir/ks.cfg',
                        self.distname,
                        image,
                        volid,
                        isoname,
                        self.release,
                        log_path_command
        )

        mock_iso_template_output = mock_iso_template.render(
                arch=self.current_arch,
                major=self.major_version,
                releasever=self.release,
                fullname=self.fullname,
                shortname=self.shortname,
                required_pkgs=required_pkgs,
                dist=self.disttag,
                repos=self.repolist,
                compose_dir_is_here=True,
                user_agent='{{ user_agent }}',
                compose_dir=self.compose_root,
        )

        mock_sh_template_output = mock_sh_template.render(
                arch=self.current_arch,
                major=self.major_version,
                releasever=self.release,
                isolation=self.mock_isolation,
                builddir=self.mock_work_root,
                shortname=self.shortname,
                isoname=isoname,
                entries_dir=entries_dir,
                image=image,
        )

        iso_template_output = iso_template.render(
                live_iso_mode=self.live_iso_mode,
                arch=self.current_arch,
                compose_live_work_dir=self.live_work_dir,
                make_image=make_image_cmd,
                live_pkg_cmd=live_pkg_cmd,
                isoname=isoname,
                major=self.major_version,
                git_clone=git_clone_cmd,
                ks_file=ks_start,
                kloc=kloc,
        )

        with open(mock_iso_path, "w+") as mip:
            mip.write(mock_iso_template_output)
            mip.close()

        with open(mock_sh_path, "w+") as msp:
            msp.write(mock_sh_template_output)
            msp.close()

        with open(iso_template_path, "w+") as itp:
            itp.write(iso_template_output)
            itp.close()

        os.chmod(mock_sh_path, 0o755)
        os.chmod(iso_template_path, 0o755)

    def _live_iso_podman_run(self, arch, images, work_root):
        """
        Does all the image building in podman containers to parallelize the
        process. This is a case where you can call this instead of looping mock
        or not run in peridot. This gives the Release Engineer a little more
        flexibility if they care enough.

        This honestly assumes you are running this on a machine that has access
        to the compose directories. It's the same as if you were doing a
        reposync of the repositories.
        """
        cmd = Shared.podman_cmd(self.log)
        entries_dir = os.path.join(work_root, "entries")
        isos_dir = self.live_work_dir
        bad_exit_list = []
        checksum_list = []
        entry_name_list = []
        self.log.warning(Color.WARN + 'There is no support for podman in empanadas.')
        self.log.warning(Color.WARN + "If this fails, it's on you to determine the fix.")
        for i in images:
            image_name = i
            entry_name = f'buildLiveImage-{arch}-{i}.sh'
            entry_name_list.append(entry_name)

            isoname = f'{arch}/{self.shortname}-{i}-{self.major_version}-{arch}-{self.date}.iso'

            checksum_list.append(isoname)

        print(entry_name_list, cmd, entries_dir)
        for pod in entry_name_list:
            podman_cmd_entry = '{} run --privileged -d -it -v "{}:{}" -v "{}:{}" --name {} --entrypoint {}/{} {}'.format(
                    cmd,
                    self.compose_root,
                    self.compose_root,
                    entries_dir,
                    entries_dir,
                    pod,
                    entries_dir,
                    pod,
                    self.container
            )

            process = subprocess.call(
                    shlex.split(podman_cmd_entry),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
            )

        join_all_pods = ' '.join(entry_name_list)
        time.sleep(3)
        self.log.info(Color.INFO + 'Building requested live images ...')

        pod_watcher = f'{cmd} wait {join_all_pods}'

        watch_man = subprocess.call(
                shlex.split(pod_watcher),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
        )

        # After the above is done, we'll check each pod process for an exit
        # code.
        pattern = "Exited (0)"
        for pod in entry_name_list:
            checkcmd = f'{cmd} ps -f status=exited -f name={pod}'
            podcheck = subprocess.Popen(
                    checkcmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True
            )

            output, errors = podcheck.communicate()
            if 'Exited (0)' not in output.decode():
                self.log.error(Color.FAIL + pod)
                bad_exit_list.append(pod)

        rmcmd = f'{cmd} rm {join_all_pods}'

        rmpod = subprocess.Popen(
                rmcmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=True
        )

        entry_name_list.clear()
        for p in checksum_list:
            path = os.path.join(isos_dir, p)
            if os.path.exists(path):
                self.log.info(Color.INFO + 'Performing checksum for ' + p)
                checksum = Shared.get_checksum(path, self.checksum, self.log)
                if not checksum:
                    self.log.error(Color.FAIL + path + ' not found! Are you sure it was built?')
                with open(path + '.CHECKSUM', "w+") as c:
                    c.write(checksum)
                    c.close()

        self.log.info(Color.INFO + 'Building live images completed')

        if len(bad_exit_list) == 0:
            self.log.info(Color.INFO + 'Live images completed successfully.')
        else:
            self.log.error(
                    Color.FAIL +
                    'There were issues with the work done. As a result, ' +
                    'some or all ISOs may not be copied later.'
            )

    def _live_iso_local_run(self, arch, image, work_root):
        """
        Runs the actual local process using mock. This is for running in
        peridot or running on a machine that does not have podman, but does
        have mock available.
        """
        entries_dir = os.path.join(work_root, "entries")
        live_dir_arch = os.path.join(self.live_work_dir, arch)
        isoname = f'{self.shortname}-{self.release}-{image}-{arch}-{self.date}.iso'
        isolink = f'{self.shortname}-{self.major_version}-{image}-{arch}-latest.iso'
        live_res_dir = f'/var/lib/mock/{self.shortname.lower()}-{self.release}-{arch}/result'

        if self.justcopyit:
            if os.path.exists(os.path.join(live_dir_arch, isoname)):
                self.log.warning(Color.WARN + 'Image already exists.')
                if self.force_build:
                    self.log.warning(Color.WARN + 'Building anyway.')
                else:
                    self.log.warning(Color.WARN + 'Skipping.')
                    return

        live_iso_cmd = f'/bin/bash {entries_dir}/liveisobuild-{arch}-{image}.sh'
        self.log.info('Starting mock build...')
        p = subprocess.call(shlex.split(live_iso_cmd))
        if p != 0:
            self.log.error('An error occured during execution.')
            self.log.error('See the logs for more information.')
            raise SystemExit()

        self.log.warning(
                Color.WARN + 'This is meant for builds done in peridot or ' +
                'locally for an end user.'
        )
        self.log.warning(
                Color.WARN +
                'If you are looping images, your built image may get ' +
                'overwritten. Ensure you have justcopyit enabled to avoid this.'
        )

        if self.justcopyit:
            self.log.info(Color.INFO + 'Copying image to work directory')
            source_path = os.path.join(live_res_dir, isoname)
            dest_path = os.path.join(live_dir_arch, isoname)
            link_path = os.path.join(live_dir_arch, isolink)
            os.makedirs(live_dir_arch, exist_ok=True)
            try:
                shutil.copy2(source_path, dest_path)
                if os.path.exists(link_path):
                    os.remove(link_path)
                os.symlink(isoname, link_path)
            except:
                self.log.error(Color.FAIL + 'We could not copy the image or create a symlink.')
                return

            self.log.info(Color.INFO + 'Generating checksum')
            checksum = Shared.get_checksum(dest_path, self.checksum, self.log)
            if not checksum:
                self.log.error(Color.FAIL + dest_path + ' not found. Did we copy it?')
                return
            with open(dest_path + '.CHECKSUM', "w+") as c:
                c.write(checksum)
                c.close()

            linksum = Shared.get_checksum(link_path, self.checksum, self.log)
            if not linksum:
                self.log.error(Color.FAIL + link_path + ' not found. Did we copy it?')
                return
            with open(link_path + '.CHECKSUM', "w+") as c:
                c.write(linksum)
                c.close()
