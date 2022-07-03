# These are shared utilities used

import os
import json
import hashlib
import shlex
import subprocess
import yaml
import productmd.treeinfo
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
            logger.error("Invalid hash type: %s" % hashtype)
            return False

        try:
            input_file = open(path, "rb")
        except IOError as e:
            logger.error("Could not open file %s: %s" % (path, e))
            return False

        while True:
            chunk = input_file.read(8192)
            if not chunk:
                break
            checksum.update(chunk)

        input_file.close()
        stat = os.stat(path)
        base = os.path.basename(path)
        # This emulates our current syncing scripts that runs stat and
        # sha256sum and what not with a very specific output.
        return "%s: %s bytes\n%s (%s) = %s\n" % (
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
        needs one.
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
    def treeinfo_modify_write():
        """
        Modifies a specific treeinfo with already available data. This is in
        the case of modifying treeinfo for primary repos or images.
        """

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
                    "version": "0.2.0",
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
            logger.error('/usr/bin/podman was not found. Good bye.')
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
            logger('/usr/bin/dnf was not found. Good bye.')
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
            logger.error('/usr/bin/git was not found. Good bye.')
            raise SystemExit("\n\n/usr/bin/git was not found.\n\nPlease "
                    " ensure that you have installed the necessary packages on "
                    " this system. "
            )
        return cmd

    @staticmethod
    def generate_conf(data, logger, dest_path='/var/tmp') -> str:
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
                "{}-{}-config.repo".format(data.shortname, data.major_version)
        )
        data.log.info('Generating the repo configuration: %s' % fname)

        if data.repo_base_url.startswith("/"):
            logger.error("Local file syncs are not supported.")
            raise SystemExit(Color.BOLD + "Local file syncs are not "
                "supported." + Color.END)

        prehashed = ''
        if data.hashed:
            prehashed = "hashed-"
        # create dest_path
        if not os.path.exists(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        config_file = open(fname, "w+")
        repolist = []
        for repo in data.repos:

            constructed_url = '{}/{}/repo/{}{}/$basearch'.format(
                    data.repo_base_url,
                    data.project_id,
                    prehashed,
                    repo,
            )

            constructed_url_src = '{}/{}/repo/{}{}/src'.format(
                    data.repo_base_url,
                    data.project_id,
                    prehashed,
                    repo,
            )

            repodata = {
                    'name': repo,
                    'baseurl': constructed_url,
                    'srcbaseurl': constructed_url_src,
                    'gpgkey': data.extra_files['git_raw_path'] + data.extra_files['gpg'][data.gpgkey]
            }
            repolist.append(repodata)

        template = data.tmplenv.get_template('repoconfig.tmpl')
        output = template.render(repos=repolist)
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
    def fpsync_method(src, dest, logger, tmp_dir):
        """
        Returns a list for the fpsync command
        """
        cmd = '/usr/bin/fpsync'
        rsync_switches = '-av --numeric-ids --no-compress --chown=10004:10005'
        if not os.path.exists(cmd):
            logger.warn(
                    '[' + Color.BOLD + Color.YELLOW + 'WARN' + Color.END + '] ' +
                    'fpsync not found'
            )
            return False

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
            logger.error(
                    '[' + Color.BOLD + Color.RED + 'FAIL' + Color.END + '] ' +
                    'fpsync failed'
            )
            return False

        if os.path.exists(dest):
            return True
        else:
            logger.error(
                    '[' + Color.BOLD + Color.RED + 'FAIL' + Color.END + '] ' +
                    'Path synced does not seem to exist for some reason.'
            )
            return False

    @staticmethod
    def rsync_method(src, dest, logger, tmp_dir):
        """
        Returns a string for the rsync command plus parallel. Yes, this is a
        hack.
        """
