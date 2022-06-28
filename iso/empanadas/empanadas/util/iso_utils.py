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
import requests
import json
import xmltodict
# if we can access s3
import boto3
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
from empanadas.util import Shared

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
            arch=None,
            hfs_compat: bool = False,
            rc: bool = False,
            s3: bool = False,
            force_download: bool = False,
            force_unpack: bool = False,
            isolation: str = 'auto',
            extra_iso=None,
            extra_iso_mode: str = 'local',
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
        self.required_pkgs = rlvars['iso_map']['lorax']['required_pkgs']
        self.mock_work_root = config['mock_work_root']
        self.lorax_result_root = config['mock_work_root'] + "/" + "lorax"
        self.mock_isolation = isolation
        self.iso_map = rlvars['iso_map']
        self.release_candidate = rc
        self.s3 = s3
        self.force_unpack = force_unpack
        self.force_download = force_download
        self.extra_iso = extra_iso
        self.extra_iso_mode = extra_iso_mode
        self.checksum = rlvars['checksum']
        self.profile = rlvars['profile']

        # Relevant major version items
        self.arch = arch
        self.arches = rlvars['allowed_arches']
        self.release = rlvars['revision']
        self.minor_version = rlvars['minor']
        self.revision = rlvars['revision'] + "-" + rlvars['rclvl']
        self.rclvl = rlvars['rclvl']
        self.repos = rlvars['iso_map']['lorax']['repos']
        self.repo_base_url = config['repo_base_url']
        self.project_id = rlvars['project_id']
        self.structure = rlvars['structure']
        self.bugurl = rlvars['bugurl']

        self.extra_files = rlvars['extra_files']

        self.container = config['container']
        if 'container' in rlvars and len(rlvars['container']) > 0:
            self.container = rlvars['container']

        self.staging_dir = os.path.join(
                    config['staging_root'],
                    config['category_stub'],
                    self.revision
        )

        # all bucket related info
        self.s3_region = config['aws_region']
        self.s3_bucket = config['bucket']
        self.s3_bucket_url = config['bucket_url']

        if s3:
            self.s3 = boto3.client('s3')

        # arch specific
        self.hfs_compat = hfs_compat

        # Templates
        file_loader = FileSystemLoader(f"{_rootdir}/templates")
        self.tmplenv = Environment(loader=file_loader)

        self.compose_latest_dir = os.path.join(
                config['compose_root'],
                major,
                "latest-Rocky-{}".format(self.profile)
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
            self.shortname.lower(), self.major_version, self.current_arch)
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

        # This is kind of a hack. Installing xorrisofs sets the alternatives to
        # it, so backwards compatibility is sort of guaranteed. But we want to
        # emulate as close as possible to what pungi does, so unless we
        # explicitly ask for xorr (in el8 and 9), we should NOT be using it.
        # For RLN and el10, we'll use xorr all the way through. When 8 is no
        # longer getting ISO's, we'll remove this section.
        required_pkgs = self.required_pkgs.copy()
        if self.iso_map['xorrisofs']:
            if 'genisoimage' in required_pkgs and 'xorriso' not in required_pkgs:
                required_pkgs.append('xorriso')

        mock_iso_template_output = mock_iso_template.render(
                arch=self.current_arch,
                major=self.major_version,
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

        self.log.info(
                '[' + Color.BOLD + Color.GREEN + 'INFO' + Color.END + '] ' +
                'Determining the latest pulls...'
        )
        if self.s3:
            latest_artifacts = self._s3_determine_latest()
        else:
            latest_artifacts = self._reqs_determine_latest()

        self.log.info(
                '[' + Color.BOLD + Color.GREEN + 'INFO' + Color.END + '] ' +
                'Downloading requested artifact(s)'
        )
        for arch in arches_to_unpack:
            lorax_arch_dir = os.path.join(
                self.lorax_work_dir,
                arch
            )

            source_path = latest_artifacts[arch]

            full_drop = '{}/lorax-{}-{}.tar.gz'.format(
                    lorax_arch_dir,
                    self.release,
                    arch
            )

            if not os.path.exists(lorax_arch_dir):
                os.makedirs(lorax_arch_dir, exist_ok=True)

            self.log.info(
                    'Downloading artifact for ' + Color.BOLD + arch + Color.END
            )
            if self.s3:
                self._s3_download_artifacts(
                        self.force_download,
                        source_path,
                        full_drop
                )
            else:
                self._reqs_download_artifacts(
                        self.force_download,
                        source_path,
                        full_drop
                )
        self.log.info(
                '[' + Color.BOLD + Color.GREEN + 'INFO' + Color.END + '] ' +
                'Download phase completed'
        )
        self.log.info(
                '[' + Color.BOLD + Color.GREEN + 'INFO' + Color.END + '] ' +
                'Beginning unpack phase...'
        )

        for arch in arches_to_unpack:
            tarname = 'lorax-{}-{}.tar.gz'.format(
                    self.release,
                    arch
            )

            tarball = os.path.join(
                    self.lorax_work_dir,
                    arch,
                    tarname
            )

            if not os.path.exists(tarball):
                self.log.error(
                        '[' + Color.BOLD + Color.RED + 'FAIL' + Color.END + '] ' +
                        'Artifact does not exist: ' + tarball
                )
                continue

            self._unpack_artifacts(self.force_unpack, arch, tarball)

        self.log.info(
                '[' + Color.BOLD + Color.GREEN + 'INFO' + Color.END + '] ' +
                'Unpack phase completed'
        )
        self.log.info(
                '[' + Color.BOLD + Color.GREEN + 'INFO' + Color.END + '] ' +
                'Beginning image variant phase'
        )

        for arch in arches_to_unpack:
            self.log.info(
                    'Copying base lorax for ' + Color.BOLD + arch + Color.END
            )
            for variant in self.iso_map['images']:
                self._copy_lorax_to_variant(self.force_unpack, arch, variant)

            self._copy_boot_to_work(self.force_unpack, arch)

        self.log.info(
                '[' + Color.BOLD + Color.GREEN + 'INFO' + Color.END + '] ' +
                'Image variant phase completed'
        )

        self.log.info(
                '[' + Color.BOLD + Color.GREEN + 'INFO' + Color.END + '] ' +
                'Beginning treeinfo phase'
        )

        for arch in arches_to_unpack:
            for variant in self.iso_map['images']:
                self.log.info(
                        'Configuring treeinfo for %s%s %s%s' % (Color.BOLD, arch, variant, Color.END)
                )

                self._treeinfo_wrapper(arch, variant)
                # Do a dirsync for non-disc data
                if not self.iso_map['images'][variant]['disc']:
                    self.log.info(
                            'Syncing repo data and images for %s%s%s' % (Color.BOLD, variant, Color.END)
                    )
                    self._copy_nondisc_to_repo(self.force_unpack, arch, variant)


    def _s3_determine_latest(self):
        """
        Using native s3, determine the latest artifacts and return a dict
        """
        temp = []
        data = {}
        try:
            self.s3.list_objects(Bucket=self.s3_bucket)['Contents']
        except:
            self.log.error(
                        '[' + Color.BOLD + Color.RED + 'FAIL' + Color.END + '] ' +
                        'Cannot access s3 bucket.'
            )
            raise SystemExit()

        for y in self.s3.list_objects(Bucket=self.s3_bucket)['Contents']:
            if 'tar.gz' in y['Key'] and self.release in y['Key']:
                temp.append(y['Key'])

        for arch in self.arches:
            temps = []
            for y in temp:
                if arch in y:
                    temps.append(y)
            temps.sort(reverse=True)
            data[arch] = temps[0]

        return data

    def _s3_download_artifacts(self, force_download, source, dest):
        """
        Download the requested artifact(s) via s3
        """
        if os.path.exists(dest):
            if not force_download:
                self.log.warn(
                        '[' + Color.BOLD + Color.YELLOW + 'WARN' + Color.END + '] ' +
                        'Artifact at ' + dest + ' already exists'
                )
                return

        self.log.info('Downloading ({}) to: {}'.format(source, dest))
        try:
            self.s3.download_file(
                    Bucket=self.s3_bucket,
                    Key=source,
                    Filename=dest
            )
        except:
            self.log.error('There was an issue downloading from %s' % self.s3_bucket)

    def _reqs_determine_latest(self):
        """
        Using requests, determine the latest artifacts and return a list
        """
        temp = []
        data = {}

        try:
            bucket_data = requests.get(self.s3_bucket_url)
        except requests.exceptions.RequestException as e:
            self.log.error('The s3 bucket http endpoint is inaccessible')
            raise SystemExit(e)

        resp = xmltodict.parse(bucket_data.content)

        for y in resp['ListBucketResult']['Contents']:
            if 'tar.gz' in y['Key'] and self.release in y['Key']:
                temp.append(y['Key'])

        for arch in self.arches:
            temps = []
            for y in temp:
                if arch in y:
                    temps.append(y)
            temps.sort(reverse=True)
            data[arch] = temps[0]

        return data

    def _reqs_download_artifacts(self, force_download, source, dest):
        """
        Download the requested artifact(s) via requests only
        """
        if os.path.exists(dest):
            if not force_download:
                self.log.warn(
                        '[' + Color.BOLD + Color.YELLOW + 'WARN' + Color.END + '] ' +
                        'Artifact at ' + dest + ' already exists'
                )
                return
        unurl = self.s3_bucket_url + '/' + source

        self.log.info('Downloading ({}) to: {}'.format(source, dest))
        try:
            with requests.get(unurl, allow_redirects=True) as r:
                with open(dest, 'wb') as f:
                    f.write(r.content)
                    f.close()
                r.close()
        except requests.exceptions.RequestException as e:
            self.log.error('There was a problem downloading the artifact')
            raise SystemExit(e)

    def _unpack_artifacts(self, force_unpack, arch, tarball):
        """
        Unpack the requested artifacts(s)
        """
        unpack_dir = os.path.join(self.lorax_work_dir, arch)
        if not force_unpack:
            file_check = os.path.join(unpack_dir, 'lorax/.treeinfo')
            if os.path.exists(file_check):
                self.log.warn(
                        '[' + Color.BOLD + Color.YELLOW + 'WARN' + Color.END + '] ' +
                        'Artifact (' + arch + ') already unpacked'
                )
                return

        self.log.info('Unpacking %s' % tarball)
        with tarfile.open(tarball) as t:
            t.extractall(unpack_dir)
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
            self.log.error(
                    '[' + Color.BOLD + Color.RED + 'FAIL' + Color.END + '] ' +
                    'Lorax base image does not exist'
            )
            return

        path_to_image = os.path.join(
                self.lorax_work_dir,
                arch,
                image
        )

        if not force_unpack:
            file_check = os.path.join(path_to_image, '.treeinfo')
            if os.path.exists(file_check):
                self.log.warn(
                        '[' + Color.BOLD + Color.YELLOW + 'WARN' + Color.END + '] ' +
                        'Lorax image for ' + image + ' already exists'
                )
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
            except:
                self.log.error(
                            '[' + Color.BOLD + Color.YELLOW + 'FAIL' + Color.END + '] ' +
                            'Cannot remove boot.iso'
                )

    def _copy_boot_to_work(self, force_unpack, arch):
        src_to_image = os.path.join(
                self.lorax_work_dir,
                arch,
                'lorax'
        )

        iso_to_go = os.path.join(
                self.iso_work_dir,
                arch
        )

        path_to_src_image = '{}/{}'.format(
                src_to_image,
                '/images/boot.iso'
        )

        rclevel = ''
        if self.release_candidate:
            rclevel = '-' + self.rclvl

        discname = '{}-{}.{}{}-{}-{}.iso'.format(
                self.shortname,
                self.major_version,
                self.minor_version,
                rclevel,
                arch,
                'boot'
        )

        isobootpath = '{}/{}'.format(
                iso_to_go,
                discname
        )

        manifest = '{}.{}'.format(
                isobootpath,
                'manifest'
        )

        if not force_unpack:
            file_check = isobootpath
            if os.path.exists(file_check):
                self.log.warn(
                        '[' + Color.BOLD + Color.YELLOW + 'WARN' + Color.END + '] ' +
                        'Boot image (' + discname + ') already exists'
                )
                return

        self.log.info('Copying %s boot iso to work directory...' % arch)
        os.makedirs(iso_to_go, exist_ok=True)
        shutil.copy2(path_to_src_image, isobootpath)
        if os.path.exists(path_to_src_image + '.manifest'):
            shutil.copy2(path_to_src_image + '.manifest', manifest)

        self.log.info('Creating checksum for %s boot iso...' % arch)
        checksum = Shared.get_checksum(isobootpath, self.checksum, self.log)
        if not checksum:
            self.log.error(
                    '[' + Color.BOLD + Color.RED + 'FAIL' + Color.END + '] ' +
                    isobootpath + ' not found! Are you sure we copied it?'
            )
            return
        with open(isobootpath + '.CHECKSUM', "w+") as c:
            c.write(checksum)
            c.close()

    def _copy_nondisc_to_repo(self, force_unpack, arch, repo):
        """
        Syncs data from a non-disc set of images to the appropriate repo. Repo
        and image MUST match names for this to work.
        """

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
        Ensure treeinfo is written correctly based on the variant passed. Each
        .treeinfo file should be configured similarly but also differently from
        the next.
        """
        image = os.path.join(self.lorax_work_dir, arch, variant)
        treeinfo = os.path.join(image, '.treeinfo')
        imagemap = self.iso_map['images'][variant]
        primary = imagemap['variant']
        repos = imagemap['repos']
        is_disc = False

        if imagemap['disc']:
            is_disc = True
            discnum = 1

        # load up productmd
        ti = productmd.treeinfo.TreeInfo()
        ti.load(treeinfo)

        # Set the name
        ti.release.name = self.distname
        ti.release.short = self.shortname
        # Set the version (the initial lorax run does this, but we are setting
        # it just in case)
        ti.release.version = self.release
        # Assign the present images into a var as a copy. For each platform,
        # clear out the present dictionary. For each item and path in the
        # assigned var, assign it back to the platform dictionary. If the path
        # is empty, continue. Do checksums afterwards.
        plats = ti.images.images.copy()
        for platform in ti.images.images:
            ti.images.images[platform] = {}
            for i, p in plats[platform].items():
                if not p:
                    continue
                if 'boot.iso' in i and is_disc:
                    continue
                ti.images.images[platform][i] = p
                ti.checksums.add(p, self.checksum, root_dir=image)

        # stage2 checksums
        if ti.stage2.mainimage:
            ti.checksums.add(ti.stage2.mainimage, self.checksum, root_dir=image)

        if ti.stage2.instimage:
            ti.checksums.add(ti.stage2.instimage, self.checksum, root_dir=image)

        # If we are a disc, set the media section appropriately.
        if is_disc:
            ti.media.discnum = discnum
            ti.media.totaldiscs = discnum

        # Create variants
        # Note to self: There's a lot of legacy stuff running around for
        # Fedora, ELN, and RHEL in general. This is the general structure,
        # apparently. But there could be a chance it'll change. We may need to
        # put in a configuration to deal with it at some point.
        #ti.variants.variants.clear()
        for y in repos:
            if y in ti.variants.variants.keys():
                vari = ti.variants.variants[y]
            else:
                vari = productmd.treeinfo.Variant(ti)

            vari.id = y
            vari.uid = y
            vari.name = y
            vari.type = "variant"
            if is_disc:
                vari.paths.repository = y
                vari.paths.packages = y + "/Packages"
            else:
                if y == primary:
                    vari.paths.repository = "."
                    vari.paths.packages = "Packages"
                else:
                    vari.paths.repository = "../../../" + y + "/" + arch + "/os"
                    vari.paths.packages = "../../../" + y + "/" + arch + "/os/Packages"

            if y not in ti.variants.variants.keys():
                ti.variants.add(vari)

            del vari

        # Set default variant
        ti.dump(treeinfo, main_variant=primary)

    # Next set of functions are loosely borrowed (in concept) from pungi. Some
    # stuff may be combined/mixed together, other things may be simplified or
    # reduced in nature.
    def run_build_extra_iso(self):
        """
        Builds DVD images based on the data created from the initial lorax on
        each arch. This should NOT be called during the usual run() section.
        """
        sync_root = self.compose_latest_sync

        self.log.info(
                '[' + Color.BOLD + Color.GREEN + 'INFO' + Color.END + '] ' +
                'Starting Extra ISOs phase'
        )

        if not os.path.exists(self.compose_base):
            self.log.info(
                    '[' + Color.BOLD + Color.RED + 'FAIL' + Color.END + '] ' +
                    'The compose directory MUST be here. Cannot continue.'
            )
            raise SystemExit()

        self._extra_iso_build_wrap()

        self.log.info('Compose repo directory: %s' % sync_root)
        self.log.info('ISO result directory: %s/$arch' % self.lorax_work_dir)
        self.log.info(
                '[' + Color.BOLD + Color.GREEN + 'INFO' + Color.END + '] ' +
                'Extra ISO phase completed.'
        )

    def _extra_iso_build_wrap(self):
        """
        Try to figure out where the build is going, we only support mock for
        now.
        """
        work_root = os.path.join(
                self.compose_latest_dir,
                'work'
        )

        arches_to_build = self.arches
        if self.arch:
            arches_to_build = [self.arch]

        images_to_build = self.iso_map['images']
        if self.extra_iso:
            images_to_build = [self.extra_iso]

        for y in images_to_build:
            if 'isoskip' in self.iso_map['images'][y] and self.iso_map['images'][y]['isoskip']:
                self.log.info(
                        '[' + Color.BOLD + Color.YELLOW + 'WARN' + Color.END + '] ' +
                        'Skipping ' + y + ' image'
                )
                continue

            for a in arches_to_build:
                lorax_path = os.path.join(self.lorax_work_dir, a, 'lorax', '.treeinfo')
                image_path = os.path.join(self.lorax_work_dir, a, y, '.treeinfo')
                if not os.path.exists(image_path):
                    self.log.error(
                            '[' + Color.BOLD + Color.RED + 'FAIL' + Color.END + '] ' +
                            'Lorax data not found for ' + y + '. Skipping.'
                    )

                    if not os.path.exists(lorax_path):
                        self.log.error(
                                '[' + Color.BOLD + Color.RED + 'FAIL' + Color.END + '] ' +
                                'Lorax not found at all. This is considered fatal.'
                        )

                    raise SystemExit()

                grafts = self._generate_graft_points(
                        a,
                        y,
                        self.iso_map['images'][y]['repos'],
                )
                self._extra_iso_local_config(a, y, grafts, work_root)

                if self.extra_iso_mode == 'local':
                    self._extra_iso_local_run(a, y, work_root)
                elif self.extra_iso_mode == 'podman':
                    continue
                else:
                    self.log.info(
                            '[' + Color.BOLD + Color.RED + 'FAIL' + Color.END + '] ' +
                            'Mode specified is not valid.'
                    )
                    raise SystemExit()

        if self.extra_iso_mode == 'podman':
            self._extra_iso_podman_run(arches_to_build, images_to_build, work_root)

    def _extra_iso_local_config(self, arch, image, grafts, work_root):
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

        mock_iso_path = '/var/tmp/lorax-{}.cfg'.format(self.major_version)
        mock_sh_path = '{}/extraisobuild-{}-{}.sh'.format(entries_dir, arch, image)
        iso_template_path = '{}/buildExtraImage-{}-{}.sh'.format(entries_dir, arch, image)
        xorriso_template_path = '{}/xorriso-{}-{}.txt'.format(entries_dir, arch, image)

        log_root = os.path.join(
                work_root,
                "logs",
                self.date_stamp
        )

        if not os.path.exists(log_root):
            os.makedirs(log_root, exist_ok=True)

        log_path_command = '| tee -a {}/{}-{}.log'.format(log_root, arch, image)

        # This is kind of a hack. Installing xorrisofs sets the alternatives to
        # it, so backwards compatibility is sort of guaranteed. But we want to
        # emulate as close as possible to what pungi does, so unless we
        # explicitly ask for xorr (in el8 and 9), we should NOT be using it.
        # For RLN and el10, we'll use xorr all the way through. When 8 is no
        # longer getting ISO's, we'll remove this section.
        required_pkgs = self.required_pkgs.copy()
        if self.iso_map['xorrisofs']:
            if 'genisoimage' in required_pkgs and 'xorriso' not in required_pkgs:
                required_pkgs.append('xorriso')

        rclevel = ''
        if self.release_candidate:
            rclevel = '-' + self.rclvl

        volid = '{}-{}-{}{}-{}-{}'.format(
                self.shortname,
                self.major_version,
                self.minor_version,
                rclevel,
                arch,
                image
        )

        isoname = '{}-{}.{}{}-{}-{}.iso'.format(
                self.shortname,
                self.major_version,
                self.minor_version,
                rclevel,
                arch,
                image
        )

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
                'use_xorrisofs': self.iso_map['xorrisofs'],
                'iso_level': self.iso_map['iso_level'],
        }

        if opts['use_xorrisofs']:
            # Generate a xorriso compatible dialog
            xp = open(grafts)
            xorpoint = xp.read()
            xp.close()
            xorriso_template_output = xorriso_template.render(
                    boot_iso=boot_iso,
                    isoname=isoname,
                    volid=volid,
                    graft=xorpoint,
            )
            xorriso_template_entry = open(xorriso_template_path, "w+")
            xorriso_template_entry.write(xorriso_template_output)
            xorriso_template_entry.close()
            opts['graft_points'] = xorriso_template_path

        make_image = '{} {}'.format(self._get_make_image_cmd(opts), log_path_command)
        isohybrid = self._get_isohybrid_cmd(opts)
        implantmd5 = self._get_implantisomd5_cmd(opts)
        make_manifest = self._get_manifest_cmd(opts)

        iso_template_output = iso_template.render(
                extra_iso_mode=self.extra_iso_mode,
                arch=arch,
                compose_work_iso_dir=self.iso_work_dir,
                make_image=make_image,
                isohybrid=isohybrid,
                implantmd5=implantmd5,
                make_manifest=make_manifest,
                lorax_pkg_cmd=lorax_pkg_cmd,
                isoname=isoname,
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

    def _extra_iso_local_run(self, arch, image, work_root):
        """
        Runs the actual local process using mock
        """
        entries_dir = os.path.join(work_root, "entries")
        extra_iso_cmd = '/bin/bash {}/extraisobuild-{}-{}.sh'.format(entries_dir, arch, image)
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
        cmd = self.podman_cmd()
        entries_dir = os.path.join(work_root, "entries")
        isos_dir = os.path.join(work_root, "isos")
        bad_exit_list = []
        checksum_list = []
        for i in images:
            entry_name_list = []
            image_name = i
            arch_sync = arches.copy()

            for a in arch_sync:
                entry_name = 'buildExtraImage-{}-{}.sh'.format(a, i)
                entry_name_list.append(entry_name)

                rclevel = ''
                if self.release_candidate:
                    rclevel = '-' + self.rclvl

                isoname = '{}/{}-{}.{}{}-{}-{}.iso'.format(
                        a,
                        self.shortname,
                        self.major_version,
                        self.minor_version,
                        rclevel,
                        a,
                        i
                )

                checksum_list.append(isoname)

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
            self.log.info(
                    '[' + Color.BOLD + Color.GREEN + 'INFO' + Color.END + '] ' +
                    'Building ' + i + ' ...'
            )
            pod_watcher = '{} wait {}'.format(
                    cmd,
                    join_all_pods
            )

            watch_man = subprocess.call(
                    shlex.split(pod_watcher),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
            )

            # After the above is done, we'll check each pod process for an exit
            # code.
            pattern = "Exited (0)"
            for pod in entry_name_list:
                checkcmd = '{} ps -f status=exited -f name={}'.format(
                        cmd,
                        pod
                )
                podcheck = subprocess.Popen(
                        checkcmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True
                )

                output, errors = podcheck.communicate()
                if 'Exited (0)' not in output.decode():
                    self.log.error(
                            '[' + Color.BOLD + Color.RED + 'FAIL' + Color.END + '] ' + pod
                    )
                    bad_exit_list.append(pod)

            rmcmd = '{} rm {}'.format(
                    cmd,
                    join_all_pods
            )

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
                    self.log.info(
                            '[' + Color.BOLD + Color.GREEN + 'INFO' + Color.END + '] ' +
                            'Performing checksum for ' + p
                    )
                    checksum = Shared.get_checksum(path, self.checksum, self.log)
                    if not checksum:
                        self.log.error(
                                '[' + Color.BOLD + Color.RED + 'FAIL' + Color.END + '] ' +
                                path + ' not found! Are you sure it was built?'
                        )
                    with open(path + '.CHECKSUM', "w+") as c:
                        c.write(checksum)
                        c.close()

            self.log.info(
                    '[' + Color.BOLD + Color.GREEN + 'INFO' + Color.END + '] ' +
                    'Building ' + i + ' completed'
            )

            if len(bad_exit_list) == 0:
                self.log.info(
                        '[' + Color.BOLD + Color.GREEN + 'INFO' + Color.END + '] ' +
                        'Copying ISOs over to compose directory...'
                )
                print()
            else:
                self.log.error(
                        '[' + Color.BOLD + Color.RED + 'FAIL' + Color.END + '] ' +
                        'There were issues with the work done. As a result, ' +
                        'the ISOs will not be copied.'
                )


    def _generate_graft_points(
            self,
            arch,
            iso,
            variants,
        ):
        """
        Get a list of packages for an extras ISO. This should NOT be called
        during the usual run() section.
        """
        lorax_base_dir = os.path.join(self.lorax_work_dir, arch)
        global_work_dir = os.path.join(self.compose_latest_dir, "work/global")

        self.log.info(
                '[' + Color.BOLD + Color.GREEN + 'INFO' + Color.END + '] ' +
                'Generating graft points for extra iso: (' + arch + ') ' + iso
        )
        files = {}
        # This is the data we need to actually boot
        lorax_for_var = os.path.join(lorax_base_dir, iso)

        if not os.path.exists(lorax_for_var + '/.treeinfo'):
            self.log.info(
                    '[' + Color.BOLD + Color.RED + 'FAIL' + Color.END + '] ' +
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

        grafts = '{}/{}-{}-grafts'.format(
                lorax_base_dir,
                iso,
                arch
        )

        xorrs = '{}/xorriso-{}.txt'.format(
                lorax_base_dir,
                arch
        )

        self._write_grafts(
                grafts,
                xorrs,
                files,
                exclude=["*/lost+found", "*/boot.iso"]
        )

        if self.iso_map['xorrisofs']:
            grafters = xorrs
        else:
            grafters = grafts

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
                tree = self._scanning(p)
            result = self._merging(result, tree)

        for p in exclusive_paths:
            tree = self._scanning(p)
            result = self._merging(result, tree, exclusive=True)

        # Resolves possible symlinks
        for key in result.keys():
            path = result[key]
            if os.path.islink(path):
                real_path = os.readlink(path)
                abspath = os.path.normpath(os.path.join(os.path.dirname(path), real_path))
                if not abspath.startswith(self.compose_base):
                    result[key] = abspath

        return result

    def _write_grafts(self, filepath, xorrspath, u, exclude=None):
        """
        Write out the graft points
        """
        seen = set()
        exclude = exclude or []
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

        if self.iso_map['xorrisofs']:
            fx = open(xorrspath, "w")
            for zm in sorted(result, key=self._sorting):
                found = False
                for excl in exclude:
                    if fnmatch(zm, excl):
                        found = True
                        break
                if found:
                    continue
                fx.write("-map %s %s\n" % (u[zm], zm))
            fx.close()
        else:
            fh = open(filepath, "w")
            for zl in sorted(result, key=self._sorting):
                found = False
                for excl in exclude:
                    if fnmatch(zl, excl):
                        found = True
                        break
                if found:
                    continue
                fh.write("%s=%s\n" % (zl, u[zl]))
            fh.close()

    def _scanning(self, p):
        """
        Scan tree
        """
        path = os.path.abspath(p)
        result = {}
        for root, dirs, files in os.walk(path):
            for file in files:
                abspath = os.path.join(root, file)
                relpath = kobo.shortcuts.relative_path(abspath, path.rstrip("/") + "/")
                result[relpath] = abspath

            # Include empty directories too
            if root != path:
                abspath = os.path.join(root, "")
                relpath = kobo.shortcuts.relative_path(abspath, path.rstrip("/") + "/")
                result[relpath] = abspath

        return result


    def _merging(self, tree_a, tree_b, exclusive=False):
        """
        Merge tree
        """
        result = tree_b.copy()
        all_dirs = set(
            [os.path.dirname(dirn).rstrip("/") for dirn in result if os.path.dirname(dirn) != ""]
        )

        for dirn in tree_a:
            dn = os.path.dirname(dirn)
            if exclusive:
                match = False
                for x in all_dirs:
                    if dn == x or dn.startswith("%s/" % x):
                        match = True
                        break
                if match:
                    continue

            if dirn in result:
                continue

            result[dirn] = tree_a[dirn]
        return result

    def _sorting(self, k):
        """
        Sorting using the is_rpm and is_image funcs. Images are first, extras
        next, rpm's last.
        """
        rolling = (0 if self._is_image(k) else 2 if self._is_rpm(k) else 1, k)
        return rolling

    def _is_rpm(self, k):
        """
        Is this an RPM? :o
        """
        result = k.endswith(".rpm")
        return result

    def _is_image(self, k):
        """
        Is this an image? :o
        """
        if (
                k.startswith("images/") or
                k.startswith("isolinux/") or
                k.startswith("EFI/") or
                k.startswith("etc/") or
                k.startswith("ppc/")
           ):
            return True

        if (
                k.endswith(".img") or
                k.endswith(".ins")
           ):
            return True

        return False

    def _get_vol_id(self):
        """
        Gets a volume ID
        """

    def _get_boot_options(self, arch, createfrom, efi=True, hfs_compat=False):
        """
        Gets boot options based on architecture, the iso commands are not
        universal.
        """
        if arch in ("armhfp",):
            result = []
            return result

        if arch in ("aarch64",):
            result = [
                    "-eltorito-alt-boot",
                    "-e",
                    "images/efiboot.img",
                    "-no-emul-boot",
            ]
            return result

        if arch in ("i386", "i686", "x86_64"):
            result = [
                    "-b",
                    "isolinux/isolinux.bin",
                    "-c",
                    "isolinux/boot.cat",
                    "-no-emul-boot",
                    "-boot-load-size",
                    "4",
                    "-boot-info-table",
            ]

            # EFI args
            if arch == "x86_64":
                result.extend(
                    [
                        "-eltorito-alt-boot",
                        "-e",
                        "images/efiboot.img",
                        "-no-emul-boot"
                    ]
                )
            return result

        # need to go double check if this is needed with stream 9
        if arch == "ppc64le" and hfs_compat:
            result = [
                    "-part",
                    "-hfs",
                    "-r",
                    "-l",
                    "-sysid",
                    "PPC",
                    "-no-desktop",
                    "-allow-multidot",
                    "-chrp-boot",
                    "-map",
                    os.path.join(createfrom, "mapping"),
                    "-hfs-bless",
                    "/ppc/mac"
            ]
            return result

        if arch == "ppc64le" and not hfs_compat:
            result = [
                    "-r",
                    "-l",
                    "-sysid",
                    "PPC",
                    "-chrp-boot",
            ]
            return result

        if arch in ("s390x",):
            result = [
                    "-eltorito-boot",
                    "images/cdboot.img",
                    "-no-emul-boot",
            ]
            return result

        raise ValueError("Architecture %s%s%s is NOT known" % (Color.BOLD, arch, Color.END))

    # ALL COMMANDS #
    def _get_mkisofs_cmd(
            self,
            iso,
            appid=None,
            volid=None,
            volset=None,
            exclude=None,
            boot_args=None,
            input_charset="utf-8",
            grafts=None,
            use_xorrisofs=False,
            iso_level=None
    ):
        # I should hardcode this I think
        #untranslated_filenames = True
        translation_table = True
        #joliet = True
        #joliet_long = True
        #rock = True
        cmd = ["/usr/bin/xorrisofs" if use_xorrisofs else "/usr/bin/genisoimage"]
        if not os.path.exists(cmd[0]):
            self.log.error('%s was not found. Good bye.' % cmd[0])
            raise SystemExit("\n\n" + cmd[0] + " was not found.\n\nPlease "
                    " ensure that you have installed the necessary packages on "
                    " this system. "
            )

        if iso_level:
            cmd.extend(["-iso-level", str(iso_level)])

        if appid:
            cmd.extend(["-appid", appid])

        #if untranslated_filenames:
        cmd.append("-untranslated-filenames")

        if volid:
            cmd.extend(["-volid", volid])

        #if joliet:
        cmd.append("-J")

        #if joliet_long:
        cmd.append("-joliet-long")

        if volset:
            cmd.extend(["-volset", volset])

        #if rock:
        cmd.append("-rational-rock")

        if not use_xorrisofs and translation_table:
            cmd.append("-translation-table")

        if input_charset:
            cmd.extend(["-input-charset", input_charset])

        if exclude:
            for i in kobo.shortcuts.force_list(exclude):
                cmd.extend(["-x", i])

        if boot_args:
            cmd.extend(boot_args)

        cmd.extend(["-o", iso])

        if grafts:
            cmd.append("-graft-points")
            cmd.extend(["-path-list", grafts])

        return cmd

    def _get_implantisomd5_cmd(self, opts):
        """
        Implants md5 into iso
        """
        cmd = ["/usr/bin/implantisomd5", "--supported-iso", opts['iso_name']]
        returned_cmd = ' '.join(cmd)
        return returned_cmd

    def _get_manifest_cmd(self, opts):
        """
        Gets an ISO manifest
        """
        if opts['use_xorrisofs']:
            return """/usr/bin/xorriso -dev %s --find |
                tail -n+2 |
                tr -d "'" |
                cut -c2-  | sort >> %s.manifest""" % (
                shlex.quote(opts['iso_name']),
                shlex.quote(opts['iso_name']),
            )
        else:
            return "/usr/bin/isoinfo -R -f -i %s | grep -v '/TRANS.TBL$' | sort >> %s.manifest" % (
                shlex.quote(opts['iso_name']),
                shlex.quote(opts['iso_name']),
            )

    def _get_isohybrid_cmd(self, opts):
        cmd = []
        if not opts['use_xorrisofs']:
            if opts['arch'] == "x86_64":
                cmd = ["/usr/bin/isohybrid"]
                cmd.append("--uefi")
                cmd.append(opts['iso_name'])
            returned_cmd = ' '.join(cmd)
        else:
            returned_cmd = ''

        return returned_cmd

    def _get_make_image_cmd(self, opts):
        """
        Generates the command to actually make the image in the first place
        """
        isokwargs = {}
        isokwargs["boot_args"] = self._get_boot_options(
                opts['arch'],
                os.path.join("$TEMPLATE", "config_files/ppc"),
                hfs_compat=self.hfs_compat,
        )

        if opts['arch'] in ("ppc64", "ppc64le"):
            isokwargs["input_charset"] = None

        if opts['use_xorrisofs']:
            cmd = ['/usr/bin/xorriso', '-dialog', 'on', '<', opts['graft_points']]
        else:
            cmd = self._get_mkisofs_cmd(
                    opts['iso_name'],
                    volid=opts['volid'],
                    exclude=["./lost+found"],
                    grafts=opts['graft_points'],
                    use_xorrisofs=False,
                    iso_level=opts['iso_level'],
                    **isokwargs
            )

        returned_cmd = ' '.join(cmd)
        return returned_cmd

    def podman_cmd(self) -> str:
        """
        This generates the podman run command. This is in the case that we want
        to do reposyncs in parallel as we cannot reasonably run multiple
        instances of dnf reposync on a single system.
        """
        cmd = None
        if os.path.exists("/usr/bin/podman"):
            cmd = "/usr/bin/podman"
        else:
            self.log.error('/usr/bin/podman was not found. Good bye.')
            raise SystemExit("\n\n/usr/bin/podman was not found.\n\nPlease "
                    " ensure that you have installed the necessary packages on "
                    " this system. " + Color.BOLD + "Note that docker is not "
                    "supported." + Color.END
            )
        return cmd

class LiveBuild:
    """
    This helps us build the live images for Rocky Linux.
    """
