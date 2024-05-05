# These are shared utilities used

import os
import json
import hashlib
import shlex
import subprocess
import shutil
import tarfile
import yaml
import requests
import boto3
import xmltodict
import productmd.treeinfo
import productmd.composeinfo
import empanadas
import kobo.shortcuts
from empanadas.common import Color

class ArchCheck:
    """
    Arches and their files
    """
    archfile = {
        'x86_64': [
                'isolinux/vmlinuz',
                'images/grub.conf',
                'EFI/BOOT/BOOTX64.EFI'
        ],
        'aarch64':  [
                'EFI/BOOT/BOOTAA64.EFI'
        ],
        'ppc64le': [
                'ppc/bootinfo.txt',
                'ppc/ppc64/vmlinuz'
        ],
        's390x': [
                'generic.ins',
                'images/generic.prm'
        ]
    }

    # These are files that can potentially change on an image.
    boot_configs = [
            "isolinux/isolinux.cfg",
            "etc/yaboot.conf",
            "ppc/ppc64/yaboot.conf",
            "EFI/BOOT/BOOTX64.conf",
            "EFI/BOOT/grub.cfg"
    ]
    boot_images = [
            "images/efiboot.img"
    ]

class Shared:
    """
    Quick utilities that may be commonly used
    """
    @staticmethod
    def get_checksum(path, hashtype, logger):
        """
        Generates a checksum from the provided path by doing things in chunks.
        This way we don't do it in memory.
        """
        try:
            checksum = hashlib.new(hashtype)
        except ValueError:
            logger.error("Invalid hash type: %s", hashtype)
            return False

        try:
            with open(path, "rb") as input_file:
                while True:
                    chunk = input_file.read(8192)
                    if not chunk:
                        break
                    checksum.update(chunk)

                input_file.close()
        except IOError as exc:
            logger.error("Could not open file %s: %s", path, exc)
            return False

        stat = os.stat(path)
        base = os.path.basename(path)
        # This emulates our current syncing scripts that runs stat and
        # sha256sum and what not with a very specific output.
        # pylint: disable=consider-using-f-string
        return "# %s: %s bytes\n%s (%s) = %s\n" % (
                base,
                stat.st_size,
                hashtype.upper(),
                base,
                checksum.hexdigest()
        )

    @staticmethod
    def treeinfo_new_write(
            file_path,
            distname,
            shortname,
            release,
            arch,
            time,
            repo
        ):
        """
        Writes really basic treeinfo, this is for single repository treeinfo
        data. This is usually called in the case of a fresh run and each repo
        needs one. This basic info may be overwritten later either by lorax
        data or a full run.
        """
        ti = productmd.treeinfo.TreeInfo()
        ti.release.name = distname
        ti.release.short = shortname
        ti.release.version = release
        ti.tree.arch = arch
        ti.tree.build_timestamp = time
        # Variants (aka repos)
        variant = productmd.treeinfo.Variant(ti)
        variant.id = repo
        variant.uid = repo
        variant.name = repo
        variant.type = "variant"
        variant.paths.repository = "."
        variant.paths.packages = "Packages"
        ti.variants.add(variant)
        ti.dump(file_path)

    @staticmethod
    def treeinfo_modify_write(data, imagemap, logger):
        """
        Modifies a specific treeinfo with already available data. This is in
        the case of modifying treeinfo for primary repos or images.
        """
        arch = data['arch']
        variant = data['variant']
        variant_path = data['variant_path']
        checksum = data['checksum']
        distname = data['distname']
        fullname = data['fullname']
        shortname = data['shortname']
        release = data['release']
        timestamp = data['timestamp']

        os_or_ks = ''
        if '/os' in variant_path or not imagemap['disc']:
            os_or_ks = 'os'
        if '/kickstart' in variant_path:
            os_or_ks = 'kickstart'

        image = os.path.join(variant_path)
        treeinfo = os.path.join(image, '.treeinfo')
        discinfo = os.path.join(image, '.discinfo')
        mediarepo = os.path.join(image, 'media.repo')
        #imagemap = self.iso_map['images'][variant]
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
        ti.release.name = distname
        ti.release.short = shortname
        # Set the version (the initial lorax run does this, but we are setting
        # it just in case)
        ti.release.version = release
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
                ti.checksums.add(p, checksum, root_dir=image)

        # stage2 checksums
        if ti.stage2.mainimage:
            ti.checksums.add(ti.stage2.mainimage, checksum, root_dir=image)

        if ti.stage2.instimage:
            ti.checksums.add(ti.stage2.instimage, checksum, root_dir=image)

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
                    vari.paths.repository = "../../../" + y + "/" + arch + "/" + os_or_ks
                    vari.paths.packages = "../../../" + y + "/" + arch + "/" + os_or_ks + "/Packages"

            if y not in ti.variants.variants.keys():
                ti.variants.add(vari)

            del vari

        # Set default variant
        logger.info('Writing treeinfo')
        ti.dump(treeinfo, main_variant=primary)
        # Set discinfo
        logger.info('Writing discinfo')
        Shared.discinfo_write(timestamp, fullname, arch, discinfo)
        # Set media.repo
        logger.info('Writing media.repo')
        Shared.media_repo_write(timestamp, fullname, mediarepo)

    @staticmethod
    def write_metadata(
            timestamp,
            datestamp,
            fullname,
            release,
            compose_id,
            file_path
    ):

        metadata = {
                "header": {
                    "name": "empanadas",
                    "version": empanadas.__version__,
                    "type": "toolkit",
                    "maintainer": "SIG/Core"
                },
                "payload": {
                    "compose": {
                        "date": datestamp,
                        "id": compose_id,
                        "fullname": fullname,
                        "release": release,
                        "timestamp": timestamp
                    }
                }
        }

        with open(file_path + ".json", "w+") as fp:
            json.dump(metadata, fp, indent=4)
            fp.close()

        with open(file_path + ".yaml", "w+") as yp:
            yaml.dump(metadata, yp)
            yp.close()

    @staticmethod
    def discinfo_write(timestamp, fullname, arch, file_path):
        """
        Ensure discinfo is written correctly
        """
        data = [
            "%s" % timestamp,
            "%s" % fullname,
            "%s" % arch,
            "ALL",
            ""
        ]

        with open(file_path, "w+") as f:
            f.write("\n".join(data))
            f.close()

    @staticmethod
    def media_repo_write(timestamp, fullname, file_path):
        """
        Ensure media.repo exists
        """
        data = [
            "[InstallMedia]",
            "name=%s" % fullname,
            "mediaid=%s" % timestamp,
            "metadata_expire=-1",
            "gpgcheck=0",
            "cost=500",
            "",
        ]

        with open(file_path, "w") as f:
            f.write("\n".join(data))

    @staticmethod
    def generate_compose_dirs(
            compose_base,
            shortname,
            version,
            date_stamp,
            logger
    ) -> str:
        """
        Generate compose dirs for full runs
        """
        compose_base_dir = os.path.join(
                compose_base,
                "{}-{}-{}".format(
                    shortname,
                    version,
                    date_stamp
                )
        )
        logger.info('Creating compose directory %s' % compose_base_dir)
        if not os.path.exists(compose_base_dir):
            os.makedirs(compose_base_dir)
            os.makedirs(compose_base_dir + '/work')
            os.makedirs(compose_base_dir + '/work/entries')
            os.makedirs(compose_base_dir + '/work/logs')
            os.makedirs(compose_base_dir + '/compose')

        return compose_base_dir

    @staticmethod
    def podman_cmd(logger) -> str:
        """
        This generates the podman run command. This is in the case that we want
        to do reposyncs in parallel as we cannot reasonably run multiple
        instances of dnf reposync on a single system.
        """
        cmd = None
        if os.path.exists("/usr/bin/podman"):
            cmd = "/usr/bin/podman"
        else:
            logger.error(Color.FAIL + '/usr/bin/podman was not found. Good bye.')
            raise SystemExit("\n\n/usr/bin/podman was not found.\n\nPlease "
                    " ensure that you have installed the necessary packages on "
                    " this system. " + Color.BOLD + "Note that docker is not "
                    "supported." + Color.END
            )
        return cmd

    @staticmethod
    def reposync_cmd(logger) -> str:
        """
        This generates the reposync command. We don't support reposync by
        itself and will raise an error.

        :return: The path to the reposync command. If dnf exists, we'll use
        that. Otherwise, fail immediately.
        """
        cmd = None
        if os.path.exists("/usr/bin/dnf"):
            cmd = "/usr/bin/dnf reposync"
        else:
            logger(Color.FAIL + '/usr/bin/dnf was not found. Good bye.')
            raise SystemExit("/usr/bin/dnf was not found. \n\n/usr/bin/reposync "
                    "is not sufficient and you are likely running on an el7 "
                    "system or a grossly modified EL8+ system, " + Color.BOLD +
                    "which tells us that you probably made changes to these tools "
                    "expecting them to work and got to this point." + Color.END)
        return cmd

    @staticmethod
    def git_cmd(logger) -> str:
        """
        This generates the git command. This is when we need to pull down extra
        files or do work from a git repository.
        """
        cmd = None
        if os.path.exists("/usr/bin/git"):
            cmd = "/usr/bin/git"
        else:
            logger.error(Color.FAIL + '/usr/bin/git was not found. Good bye.')
            raise SystemExit("\n\n/usr/bin/git was not found.\n\nPlease "
                    " ensure that you have installed the necessary packages on "
                    " this system. "
            )
        return cmd

    @staticmethod
    def mock_cmd(logger) -> str:
        """
        This generates the mock command. This is when we are building or
        performing any kind of operation in mock.
        """
        cmd = None
        if os.path.exists("/usr/bin/mock"):
            cmd = "/usr/bin/mock"
        else:
            logger.error(Color.FAIL + '/usr/bin/mock was not found. Good bye.')
            raise SystemExit("\n\n/usr/bin/mock was not found.\n\nPlease "
                    " ensure that you have installed the necessary packages on "
                    " this system. "
            )
        return cmd

    @staticmethod
    def rsync_cmd(logger) -> str:
        """
        This generates the rsync command. This is used for general syncing
        operations.
        """
        cmd = None
        if os.path.exists("/usr/bin/rsync"):
            cmd = "/usr/bin/rsync"
        else:
            logger.error(Color.FAIL + '/usr/bin/rsync was not found. Good bye.')
            raise SystemExit("\n\n/usr/bin/rsync was not found.\n\nPlease "
                    " ensure that you have installed the necessary packages on "
                    " this system. "
            )
        return cmd

    @staticmethod
    def generate_conf(
            shortname,
            major_version,
            repos,
            repo_base_url,
            project_id,
            hashed,
            extra_files,
            gpgkey,
            gpg_check,
            repo_gpg_check,
            templates,
            logger,
            dest_path='/var/tmp'
        ) -> str:
        """
        Generates the necessary repo conf file for the operation. This repo
        file should be temporary in nature. This will generate a repo file
        with all repos by default. If a repo is chosen for sync, that will be
        the only one synced.

        :param dest_path: The destination where the temporary conf goes
        :param repo: The repo object to create a file for
        """
        fname = os.path.join(
                dest_path,
                "{}-{}-config.repo".format(shortname, major_version)
        )
        logger.info('Generating the repo configuration: %s' % fname)

        if repo_base_url.startswith("/"):
            logger.error("Local file syncs are not supported.")
            raise SystemExit(Color.BOLD + "Local file syncs are not "
                "supported." + Color.END)

        prehashed = ''
        if hashed:
            prehashed = "hashed-"
        # create dest_path
        if not os.path.exists(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        config_file = open(fname, "w+")
        repolist = []
        for repo in repos:

            constructed_url = '{}/{}/repo/{}{}/$basearch'.format(
                    repo_base_url,
                    project_id,
                    prehashed,
                    repo,
            )

            constructed_url_src = '{}/{}/repo/{}{}/src'.format(
                    repo_base_url,
                    project_id,
                    prehashed,
                    repo,
            )

            repodata = {
                    'name': repo,
                    'baseurl': constructed_url,
                    'srcbaseurl': constructed_url_src,
                    'gpgkey': extra_files['git_raw_path'] + extra_files['gpg'][gpgkey]
            }
            repolist.append(repodata)

        template = templates.get_template('repoconfig.tmpl')
        output = template.render(
                repos=repolist,
                gpg_check=gpg_check,
                repo_gpg_check=repo_gpg_check
        )
        config_file.write(output)

        config_file.close()
        return fname

    @staticmethod
    def quick_sync(src, dest, logger, tmp_dir):
        """
        Does a quick sync from one place to another. This determines the method
        in which will be used. We will look for fpsync and fall back to
        parallel | rsync if that is also available. It will fail if parallel is
        not available.

        Return true or false on completion?
        """

    @staticmethod
    def simple_sync(src, dest):
        """
        This is for simple syncs only, using rsync or copytree.
        """

    @staticmethod
    def fpsync_method(src, dest, tmp_dir):
        """
        Returns a list for the fpsync command
        """
        cmd = '/usr/bin/fpsync'
        #rsync_switches = '-av --numeric-ids --no-compress --chown=10004:10005'
        rsync_switches = '-v --numeric-ids --no-compress --chown=10004:10005'
        if not os.path.exists(cmd):
            message = 'fpsync not found'
            retval = 1
            return message, retval

        os.makedirs(tmp_dir, exist_ok=True)

        fpsync_cmd = '{} -o "{}" -n 18 -t {} {} {}'.format(
                cmd,
                rsync_switches,
                tmp_dir,
                src,
                dest
        )

        process = subprocess.call(
                shlex.split(fpsync_cmd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
        )

        if process != 0:
            message = 'Syncing (fpsync) failed'
            retval = process
            return message, retval

        if os.path.exists(dest):
            message = 'Syncing (fpsync) succeeded'
            retval = process
        else:
            message = 'Path synced does not seem to exist for some reason.'
            retval = 1

        #shutil.rmtree(tmp_dir)

        return message, retval

    @staticmethod
    def rsync_method(src, dest):
        """
        Returns a string for the rsync command plus parallel. Yes, this is a
        hack.
        """
        #find_cmd = '/usr/bin/find'
        #parallel_cmd = '/usr/bin/parallel'
        cmd = '/usr/bin/rsync'
        switches = '-vrlptDSH --chown=10004:10005 --progress --human-readable'
        rsync_command = f'{cmd} {switches} {src}/ {dest}'

        #os.makedirs(dest, exist_ok=True)
        process = subprocess.call(
                shlex.split(rsync_command),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
        )
        if process != 0:
            message = 'Syncing (rsync) failed'
            retval = process
            return message, retval

        if os.path.exists(dest):
            message = 'Syncing (rsync) succeeded'
            retval = process
        else:
            message = 'Path synced does not seem to exist for some reason.'
            retval = 1

        return message, retval

    # pylint: disable=too-many-locals,too-many-arguments
    @staticmethod
    def s3_determine_latest(s3_bucket, release, arches, filetype, name,
                            root_prefix, logger):
        """
        Using native s3, determine the latest artifacts and return a dict
        """
        temp = []
        data = {}
        s3 = boto3.client('s3')

        try:
            res = s3.list_objects_v2(Bucket=s3_bucket)
        except:
            logger.error(
                        '[' + Color.BOLD + Color.RED + 'FAIL' + Color.END + '] ' +
                        'Cannot access s3 bucket.'
            )
            raise SystemExit()

        objs = res['Contents']

        while True:
            for y in objs:
                key = y['Key']
                if key.endswith(filetype) and release in key and name in key:
                    temp.append(y['Key'])
            next_token = res.get("NextContinuationToken", None)
            if next_token:
                res = s3.list_objects_v2(Bucket=s3_bucket, ContinuationToken=next_token)
                objs = res['Contents']
            else:
                break

        for arch in arches:
            temps = []
            start_of_path = f'{root_prefix}-{release.split('.')[0]}-{arch}'
            for y in temp:
                if arch in y and start_of_path in y:
                    temps.append(y)
            temps.sort(reverse=True)
            if len(temps) > 0:
                data[arch] = temps[0]

        return data

    @staticmethod
    def s3_download_artifacts(force_download, s3_bucket, source, dest, logger):
        """
        Download the requested artifact(s) via s3
        """
        s3 = boto3.client('s3')
        if os.path.exists(dest):
            if not force_download:
                logger.warning(
                        '[' + Color.BOLD + Color.YELLOW + 'WARN' + Color.END + '] ' +
                        'Artifact at ' + dest + ' already exists'
                )
                return

        logger.info('Downloading ({}) to: {}'.format(source, dest))
        try:
            s3.download_file(
                    Bucket=s3_bucket,
                    Key=source,
                    Filename=dest
            )
        except:
            logger.error('There was an issue downloading from %s' % s3_bucket)


    @staticmethod
    def reqs_determine_latest(s3_bucket_url, release, arches, filetype, name, logger, page_size=1000):
        """
        Using requests, determine the latest artifacts and return a list
        """
        temp = []
        data = {}
        marker = None

        # Hardcoding this for now until we can come up with a better solution
        if 'lorax' in name:
            prefix = "buildiso"
        else:
            prefix = "buildimage"

        while True:
            params = {}
            if marker:
                params['marker'] = marker
            params['prefix'] = f"{prefix}-{release.split('.')[0]}-"
            params['max-keys'] = str(page_size)

            try:
                bucket_data = requests.get(s3_bucket_url, params=params, timeout=100)
            except requests.exceptions.RequestException as exception:
                logger.error('The s3 bucket http endpoint is inaccessible')
                raise SystemExit(exception) from exception

            resp = xmltodict.parse(bucket_data.content)

            if 'Contents' in resp['ListBucketResult'].keys():
                for y in resp['ListBucketResult']['Contents']:
                    if y['Key'].endswith(filetype) and release in y['Key'] and name in y['Key']:
                        temp.append(y['Key'])

            for arch in arches:
                temps = []
                for y in temp:
                    if arch in y:
                        temps.append(y)
                temps.sort(reverse=True)
                if len(temps) > 0:
                    data[arch] = temps[0]

            truncated = resp['ListBucketResult'].get('IsTruncated')

            # break from loop if there are no more results
            if truncated == 'false':
                break

            # If truncated was true, we must set the marker for the next request to the last key of the current response
            # ListObjects does not return NextMarker unless using Delimiter.. which is annoying
            next_key = resp['ListBucketResult']['Contents'][-1].get('Key')
            logger.info(Color.INFO + 'requesting another page starting with key: %s', next_key)
            marker = next_key

        return data

    @staticmethod
    def reqs_download_artifacts(force_download, s3_bucket_url, source, dest, logger):
        """
        Download the requested artifact(s) via requests only
        """
        if os.path.exists(dest):
            if not force_download:
                logger.warning(
                        '[' + Color.BOLD + Color.YELLOW + 'WARN' + Color.END + '] ' +
                        'Artifact at ' + dest + ' already exists'
                )
                return
        unurl = s3_bucket_url + '/' + source

        logger.info('Downloading ({}) to: {}'.format(source, dest))
        try:
            with requests.get(unurl, allow_redirects=True) as r:
                with open(dest, 'wb') as f:
                    f.write(r.content)
                    f.close()
                r.close()
        except requests.exceptions.RequestException as e:
            logger.error('There was a problem downloading the artifact')
            raise SystemExit(e)

    # ISO related
    @staticmethod
    def get_boot_options(arch, createfrom, efi=True, hfs_compat=False):
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

    @staticmethod
    def get_mkisofs_cmd(
            iso,
            appid=None,
            volid=None,
            volset=None,
            exclude=None,
            boot_args=None,
            input_charset="utf-8",
            grafts=None,
            use_xorrisofs=False,
            iso_level=None,
    ):
        # I should hardcode this I think
        #untranslated_filenames = True
        translation_table = True
        #joliet = True
        #joliet_long = True
        #rock = True
        cmd = ["/usr/bin/xorrisofs" if use_xorrisofs else "/usr/bin/genisoimage"]
        if not os.path.exists(cmd[0]):
            #logger.error('%s was not found. Good bye.' % cmd[0])
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

    @staticmethod
    def get_make_image_cmd(opts, hfs_compat):
        """
        Generates the command to actually make the image in the first place
        """
        isokwargs = {}
        isokwargs["boot_args"] = Shared.get_boot_options(
                opts['arch'],
                os.path.join("$TEMPLATE", "config_files/ppc"),
                hfs_compat=hfs_compat,
        )

        if opts['arch'] in ("ppc64", "ppc64le"):
            isokwargs["input_charset"] = None

        if opts['use_xorrisofs']:
            cmd = [
                    '/usr/bin/xorriso',
                    '-dialog',
                    'on',
                    '<',
                    opts['graft_points'],
                    '2>&1'
            ]
        else:
            cmd = Shared.get_mkisofs_cmd(
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

    @staticmethod
    def get_isohybrid_cmd(opts):
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

    @staticmethod
    def get_implantisomd5_cmd(opts):
        """
        Implants md5 into iso
        """
        cmd = ["/usr/bin/implantisomd5", "--supported-iso", opts['iso_name']]
        returned_cmd = ' '.join(cmd)
        return returned_cmd

    @staticmethod
    def get_manifest_cmd(opts):
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

    @staticmethod
    def build_repo_list(
            repo_base_url,
            repos,
            project_id,
            current_arch,
            compose_latest_sync,
            compose_dir_is_here: bool = False,
            hashed: bool = False,
            extra_repos: list = None
        ):
        """
        Builds the repo dictionary
        """
        repolist = []
        prehashed = ''
        if hashed:
            prehashed = 'hashed-'

        for name in repos:
            if not compose_dir_is_here:
                constructed_url = '{}/{}/repo/{}{}/{}'.format(
                        repo_base_url,
                        project_id,
                        prehashed,
                        name,
                        current_arch
                )
            else:
                constructed_url = 'file://{}/{}/{}/os'.format(
                        compose_latest_sync,
                        name,
                        current_arch
                )


            repodata = {
                'name': name,
                'url': constructed_url
            }

            repolist.append(repodata)

        if extra_repos:
            repolist.append(repo for repo in Shared.parse_extra_repos(extra_repos))

        return repolist

    @staticmethod
    def parse_extra_repos(extra_repos: list) -> list:
        # must be in format URL[,PRIORITY]
        result = []
        for idx, candidate in enumerate(extra_repos):
            url, priority = candidate.split(',')
            if not priority:
                priority = 100
            result.append({
                'name': f"extra_repo_{idx}",
                'url': url,
                'priority': priority
                })
        return result

    @staticmethod
    def composeinfo_write(
            compose_path,
            distname,
            shortname,
            release,
            release_type,
            datestamp,
            arches: list = [],
            repos: list = []
        ):
        """
        Write compose info similar to pungi.

        arches and repos may be better suited for a dictionary. that is a
        future thing we will work on for 0.5.0.
        """
        metadata_dir = compose_path + '/metadata'
        composeinfo_path = metadata_dir + '/composeinfo'
        cijson = composeinfo_path + '.json'
        ciyaml = composeinfo_path + '.yaml'
        ci = productmd.composeinfo.ComposeInfo()
        ci.release.name = distname
        ci.release.short = shortname
        ci.release.version = release
        ci.release.type = release_type

        ci.compose.id = '{}-{}-{}'.format(shortname, release, datestamp)
        ci.compose.type = "production"
        ci.compose.date = datestamp
        ci.compose.respin = 0

        for repo in repos:
            variant_repo = productmd.composeinfo.Variant(ci)
            variant_repo.id = repo
            variant_repo.uid = repo
            variant_repo.name = repo
            variant_repo.type = "variant"
            variant_repo.arches = set(arches)
            # directories...
            # if the repo is BaseOS, set the "isos" to isos/ARCH
            for arch in variant_repo.arches:
                variant_repo.paths.os_tree[arch] = repo + "/" + arch + "/os"
                variant_repo.paths.repository[arch] = repo + "/" + arch + "/os"
                variant_repo.paths.packages[arch] = repo + "/" + arch + "/os/Packages"
                # Debug
                variant_repo.paths.debug_packages[arch] = repo + "/" + arch + "/debug/tree/Packages"
                variant_repo.paths.debug_repository[arch] = repo + "/" + arch + "/debug/tree"
                variant_repo.paths.debug_tree[arch] = repo + "/" + arch + "/debug/tree"
                # Source
                variant_repo.paths.source_packages[arch] = repo + "/source/tree/Packages"
                variant_repo.paths.source_repository[arch] = repo + "/source/tree"
                variant_repo.paths.source_tree[arch] = repo + "/source/tree"

                if "BaseOS" or "Minimal" in repo:
                    variant_repo.paths.isos[arch] = "isos/" + arch
                    variant_repo.paths.images[arch] = "images/" + arch

            ci.variants.add(variant_repo)

        ci.dump(cijson)

        with open(cijson, 'r') as cidump:
            jsonData = json.load(cidump)
            cidump.close()

        with open(ciyaml, 'w+') as ymdump:
            yaml.dump(jsonData, ymdump)
            ymdump.close()

    @staticmethod
    def symlink_to_latest(shortname, major_version, generated_dir, compose_latest_dir, logger):
        """
        Emulates pungi and symlinks latest-Rocky-X
        This link will be what is updated in full runs. Whatever is in this
        'latest' directory is what is rsynced on to staging after completion.
        This link should not change often.
        """
        try:
            os.remove(compose_latest_dir)
        except:
            pass

        logger.info('Symlinking to latest-{}-{}...'.format(shortname, major_version))
        os.symlink(generated_dir, compose_latest_dir)

    @staticmethod
    def deploy_extra_files(extra_files, sync_root, global_work_root, logger):
        """
        deploys extra files based on info of rlvars including a
        extra_files.json

        might also deploy COMPOSE_ID and maybe in the future a metadata dir with
        a bunch of compose-esque stuff.
        """
        #logger.info(Color.INFO + 'Deploying treeinfo, discinfo, and media.repo')

        cmd = Shared.git_cmd(logger)
        tmpclone = '/tmp/clone'
        extra_files_dir = os.path.join(
                global_work_root,
                'extra-files'
        )
        metadata_dir = os.path.join(
                sync_root,
                "metadata"
        )
        if not os.path.exists(extra_files_dir):
            os.makedirs(extra_files_dir, exist_ok=True)

        if not os.path.exists(metadata_dir):
            os.makedirs(metadata_dir, exist_ok=True)

        clonecmd = '{} clone {} -b {} -q {}'.format(
                cmd,
                extra_files['git_repo'],
                extra_files['branch'],
                tmpclone
        )

        git_clone = subprocess.call(
                shlex.split(clonecmd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
        )

        logger.info(Color.INFO + 'Deploying extra files to work and metadata directories ...')

        # Copy files to work root
        for extra in extra_files['list']:
            src = '/tmp/clone/' + extra
            # Copy extra files to root of compose here also - The extra files
            # are meant to be picked up by our ISO creation process and also
            # exist on our mirrors.
            try:
                shutil.copy2(src, extra_files_dir)
                shutil.copy2(src, metadata_dir)
            except:
                logger.warning(Color.WARN + 'Extra file not copied: ' + src)

        try:
            shutil.rmtree(tmpclone)
        except OSError as e:
            logger.error(Color.FAIL + 'Directory ' + tmpclone +
                    ' could not be removed: ' + e.strerror
            )

    @staticmethod
    def tar_is_within_directory(directory, target):
        """
        CVE-2007-4559
        """
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
        prefix = os.path.commonprefix([abs_directory, abs_target])
        return prefix == abs_directory

    @staticmethod
    def tar_safe_extractall(tar,
            path=".",
            members=None,
            *,
            numeric_owner=False
        ):
        """
        CVE-2007-4559
        """
        for member in tar.getmembers():
            member_path = os.path.join(path, member.name)
            if not Shared.tar_is_within_directory(path, member_path):
                raise Exception("Path traversal attempted in tar file")

        tar.extractall(path=path, members=members, numeric_owner=numeric_owner)

    @staticmethod
    def dnf_sync(repo, sync_root, work_root, arch, logger):
        """
        This is for normal dnf syncs. This is very slow.
        """
        logger.error('DNF syncing has been removed.')
        logger.error('Please install podman and enable parallel')
        raise SystemExit()

    @staticmethod
    def norm_dnf_sync(data, repo, sync_root, work_root, arch, logger):
        """
        This is for normal dnf syncs. This is very slow.
        """
        cmd = Shared.reposync_cmd(logger)
        sync_single_arch = False
        arches_to_sync = data.arches
        if arch:
            sync_single_arch = True
            arches_to_sync = [arch]

        logger.info(
                Color.BOLD + '!! WARNING !! ' + Color.END + 'You are performing a '
                'local reposync, which will incur delays in your compose.'
        )

        if data.fullrun:
            logger.info(
                    Color.BOLD + '!! WARNING !! ' + Color.END + 'This is a full '
                    'sync. Expect a few days for it to complete.'
            )

        for r in repos_to_sync:
            for a in arches_to_sync:
                repo_name = r
                if r in data.repo_renames:
                    repo_name = data.repo_renames[r]

                os_sync_path = os.path.join(
                        sync_root,
                        repo_name,
                        a,
                        'os'
                )

                debug_sync_path = os.path.join(
                        sync_root,
                        repo_name,
                        a,
                        'debug/tree'
                )

                sync_cmd = "{} -c {} --download-metadata --repoid={} -p {} --forcearch {} --norepopath".format(
                        cmd,
                        data.dnf_config,
                        r,
                        os_sync_path,
                        a
                )

                debug_sync_cmd = "{} -c {} --download-metadata --repoid={}-debug -p {} --forcearch {} --norepopath".format(
                        cmd,
                        data.dnf_config,
                        r,
                        debug_sync_path,
                        a
                )

                logger.info('Syncing {} {}'.format(r, a))
                #logger.info(sync_cmd)
                # Try to figure out where to send the actual output of this...
                # Also consider on running a try/except here? Basically if
                # something happens (like a repo doesn't exist for some arch,
                # eg RT for aarch64), make a note of it somehow (but don't
                # break the entire sync). As it stands with this
                # implementation, if something fails, it just continues on.
                process = subprocess.call(
                        shlex.split(sync_cmd),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                )

                if not data.ignore_debug:
                    logger.info('Syncing {} {} (debug)'.format(r, a))
                    process_debug = subprocess.call(
                            shlex.split(debug_sync_cmd),
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                    )

                # There should be a check here that if it's "all" and multilib
                # is on, i686 should get synced too.

            if not data.ignore_source:
                source_sync_path = os.path.join(
                    sync_root,
                    repo_name,
                    'source/tree'
                )

                source_sync_cmd = "{} -c {} --download-metadata --repoid={}-source -p {} --norepopath".format(
                    cmd,
                    data.dnf_config,
                    r,
                    source_sync_path
                )


                logger.info('Syncing {} source'.format(r))
                process_source = subprocess.call(
                        shlex.split(source_sync_cmd),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                )

        logger.info('Syncing complete')

class Idents:
    """
    Identifiers or locators
    """
    @staticmethod
    def scanning(p):
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

    @staticmethod
    def merging(tree_a, tree_b, exclusive=False):
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

    @staticmethod
    def sorting(k):
        """
        Sorting using the is_rpm and is_image funcs. Images are first, extras
        next, rpm's last.
        """
        rolling = (0 if Idents.is_image(k) else 2 if Idents.is_rpm(k) else 1, k)
        return rolling

    @staticmethod
    def is_rpm(k):
        """
        Is this an RPM? :o
        """
        result = k.endswith(".rpm")
        return result

    @staticmethod
    def is_image(k):
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

    @staticmethod
    def get_vol_id(opts):
        """
        Gets a volume ID
        """

class Syncs:
    """
    Various rsync abilities, converted from the sync dir in the toolkit
    """
