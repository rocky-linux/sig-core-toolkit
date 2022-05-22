"""
Syncs yum repos for mirroring and composing.

Louis Abel <label AT rockylinux.org>
"""
#import shutil
import logging
import sys
import os
import os.path
#import pipes
from common import Color

#HAS_LIBREPO = True
#try:
#    import librepo
#except:
#    HAS_LIBREPO = False

class RepoSync:
    """
    This helps us do reposync operations for the base system. SIG syncs are a
    different class entirely. This is on purpose. Please use the SigRepoSync
    class for SIG syncs.
    """
    def __init__(
            self,
            rlvars,
            config,
            major,
            repo=None,
            arch=None,
            ignore_debug=False,
            ignore_source=False,
            dryrun: bool = False,
            fullrun: bool = False,
            nofail: bool = False,
            logger=None
        ):
        self.nofail = nofail
        self.dryrun = dryrun
        self.fullrun = fullrun
        self.arch = arch
        self.ignore_debug = ignore_debug
        self.ignore_source = ignore_source
        # Relevant config items
        self.major_version = major
        self.date_stamp = config['date_stamp']
        self.repo_base_url = config['repo_base_url']
        self.compose_base = config['compose_root'] + "/" + major

        # Relevant major version items
        self.revision = rlvars['revision'] + "-" + rlvars['rclvl']
        self.arches = rlvars['allowed_arches']
        self.project_id = rlvars['project_id']
        self.repo_renames = rlvars['renames']
        self.repos = rlvars['all_repos']
        self.repo = repo

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

        # This is temporary for now.
        if logger is None:
            self.log = logging.getLogger("reposync")
            self.log.setLevel(logging.INFO)
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                    '%(asctime)s :: %(name)s :: %(message)s',
                    '%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.log.addHandler(handler)

        self.log.info('reposync init')
        self.log.info(self.revision)

    def run(self):
        """
        This must be called to perform the sync. This will run through, create
        the configuration file as required, and try to do a sync of every repo
        applicable or the repo actually specified. If self.repo is None, it
        will be assumed all repos are synced as dictated by rlvars.

         * Dry runs only create initial directories and structure
         * Full runs sync everything from the top and setup structure,
           including creating a symlink to latest-Rocky-X
         * self.repo is ignored during full runs (noted in stdout)
         * self.arch being set will force only that arch to sync
        """
        if self.fullrun and self.repo:
            self.log.error('WARNING: repo ignored when doing a full sync')
        if self.fullrun and self.dryrun:
            self.log.error('A full and dry run is currently not supported.')
            raise SystemExit('\nA full and dry run is currently not supported.')

        self.generate_conf()

        if self.fullrun:
            sync_root = os.path.join(
                    self.generate_compose_dirs(),
                    'compose'
            )
        else:
            sync_root = self.compose_latest_sync

    def sync(self, repo, sync_root, arch=None):
        """
        Does the actual syncing of the repo. We generally sync each component
        of a repo:
            * each architecture
            * each architecture debug
            * each source
        """
        # dnf reposync --download-metadata \
        #       --repoid fedora -p /tmp/test \
        #       --forcearch aarch64 --norepopath
        cmd = self.reposync_cmd()

    def generate_compose_dirs(self) -> str:
        """
        Generate compose dirs for full runs
        """
        compose_base_dir = os.path.join(
                self.compose_base,
                "Rocky-{}-{}".format(self.major_version, self.date_stamp)
        )
        self.log.info('Creating compose directory %s' % compose_base_dir)
        if not os.path.exists(compose_base_dir):
            os.makedirs(compose_base_dir)

        return compose_base_dir

    def symlink_to_latest(self):
        """
        Emulates pungi and symlinks latest-Rocky-X

        This link will be what is updated in full runs. Whatever is in this
        'latest' directory is what is rsynced on to staging after completion.
        This link should not change often.
        """
        pass

    def generate_conf(self, dest_path='/var/tmp'):
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
                "{}-config.repo".format(self.major_version)
        )
        self.log.info('Generating the repo configuration: %s' % fname)

        if self.repo_base_url.startswith("/"):
            self.log.error("Local file syncs are not supported.")
            raise SystemExit(Color.BOLD + "Local file syncs are not "
                "supported." + Color.END)

        # create dest_path
        if not os.path.exists(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        config_file = open(fname, "w+")
        for repo in self.repos:
            constructed_url = '{}/{}/repo/{}/$basearch'.format(
                    self.repo_base_url,
                    self.project_id,
                    repo,
            )

            constructed_url_debug = '{}/{}/repo/{}/$basearch-debug'.format(
                    self.repo_base_url,
                    self.project_id,
                    repo,
            )

            constructed_url_src = '{}/{}/repo/{}/src'.format(
                    self.repo_base_url,
                    self.project_id,
                    repo,
            )

            # normal
            config_file.write('[%s]\n' % repo)
            config_file.write('name=%s\n' % repo)
            config_file.write('baseurl=%s\n' % constructed_url)
            config_file.write("enabled=1\n")
            config_file.write("gpgcheck=0\n\n")

            # debug
            config_file.write('[%s-debug]\n' % repo)
            config_file.write('name=%s debug\n' % repo)
            config_file.write('baseurl=%s\n' % constructed_url_debug)
            config_file.write("enabled=1\n")
            config_file.write("gpgcheck=0\n\n")

            # src
            config_file.write('[%s-source]\n' % repo)
            config_file.write('name=%s source\n' % repo)
            config_file.write('baseurl=%s\n' % constructed_url_src)
            config_file.write("enabled=1\n")
            config_file.write("gpgcheck=0\n\n")



    def reposync_cmd(self) -> str:
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
            self.log.error('/usr/bin/dnf was not found. Good bye.')
            raise SystemExit("/usr/bin/dnf was not found. \n\n/usr/bin/reposync "
                    "is not sufficient and you are likely running on an el7 "
                    "system or a grossly modified EL8+ system, " + Color.BOLD +
                    "which tells us that you probably made changes to these tools "
                    "expecting them to work and got to this point." + Color.END)
        return cmd

class SigRepoSync:
    """
    This helps us do reposync operations for SIG's. Do not use this for the
    base system. Use RepoSync for that.
    """
