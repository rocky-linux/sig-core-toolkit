"""
Syncs yum repos for mirroring and composing.

Louis Abel <label AT rockylinux.org>
"""
#import shutil
import logging
import sys
import os
import os.path
import subprocess
import shlex
import time
import re
import json
#import pipes
from common import Color
from jinja2 import Environment, FileSystemLoader

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
            ignore_debug: bool = False,
            ignore_source: bool = False,
            repoclosure: bool = False,
            skip_all: bool = False,
            hashed: bool = False,
            parallel: bool = False,
            dryrun: bool = False,
            fullrun: bool = False,
            nofail: bool = False,
            gpgkey: str = 'stable',
            logger=None
        ):
        self.nofail = nofail
        self.dryrun = dryrun
        self.fullrun = fullrun
        self.arch = arch
        self.ignore_debug = ignore_debug
        self.ignore_source = ignore_source
        self.skip_all = skip_all
        self.hashed = hashed
        self.repoclosure = repoclosure
        # Enables podman syncing, which should effectively speed up operations
        self.parallel = parallel
        # Relevant config items
        self.major_version = major
        self.date_stamp = config['date_stamp']
        self.repo_base_url = config['repo_base_url']
        self.compose_root = config['compose_root']
        self.compose_base = config['compose_root'] + "/" + major

        # Relevant major version items
        self.shortname = config['shortname']
        self.revision = rlvars['revision'] + "-" + rlvars['rclvl']
        self.fullversion = rlvars['revision']
        self.arches = rlvars['allowed_arches']
        self.project_id = rlvars['project_id']
        self.repo_renames = rlvars['renames']
        self.repos = rlvars['all_repos']
        self.multilib = rlvars['provide_multilib']
        self.repo = repo
        self.extra_files = rlvars['extra_files']
        self.gpgkey = gpgkey

        # Templates
        file_loader = FileSystemLoader('templates')
        self.tmplenv = Environment(loader=file_loader)

        # each el can have its own designated container to run stuff in,
        # otherwise we'll just default to the default config.
        self.container = config['container']
        if 'container' in rlvars and len(rlvars['container']) > 0:
            self.container = rlvars['container']

        if 'repoclosure_map' in rlvars and len(rlvars['repoclosure_map']) > 0:
            self.repoclosure_map = rlvars['repoclosure_map']

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
        self.dnf_config = self.generate_conf()


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

        # This should create the initial compose dir and set the path.
        # Otherwise, just use the latest link.
        if self.fullrun:
            generated_dir = self.generate_compose_dirs()
            work_root = os.path.join(
                    generated_dir,
                    'work'
            )
            sync_root = os.path.join(
                    generated_dir,
                    'compose'
            )
        else:
            # Put in a verification here.
            work_root = os.path.join(
                    self.compose_latest_dir,
                    'work'
            )
            sync_root = self.compose_latest_sync

            # Verify if the link even exists
            if not os.path.exists(self.compose_latest_dir):
                self.log.error('!! Latest compose link is broken does not exist: %s' % self.compose_latest_dir)
                self.log.error('!! Please perform a full run if you have not done so.')
                raise SystemExit()

        log_root = os.path.join(
                work_root,
                "logs",
                self.date_stamp
        )

        if self.dryrun:
            self.log.error('Dry Runs are not supported just yet. Sorry!')
            raise SystemExit()

        self.sync(self.repo, sync_root, work_root, log_root, self.arch)

        if self.fullrun:
            self.deploy_extra_files()
            self.symlink_to_latest(generated_dir)

        if self.repoclosure:
            self.repoclosure_work(sync_root, work_root, log_root)

        self.log.info('Compose repo directory: %s' % sync_root)
        self.log.info('Compose logs: %s' % log_root)
        self.log.info('Compose completed.')

    def sync(self, repo, sync_root, work_root, log_root, arch=None):
        """
        Calls out syncing of the repos. We generally sync each component of a
        repo:
            * each architecture
            * each architecture debug
            * each source

        If parallel is true, we will run in podman.
        """
        if self.parallel:
            self.podman_sync(repo, sync_root, work_root, log_root, arch)
        else:
            self.dnf_sync(repo, sync_root, work_root, arch)

    def dnf_sync(self, repo, sync_root, work_root, arch):
        """
        This is for normal dnf syncs. This is very slow.
        """
        self.log.error('DNF syncing has been removed.')
        self.log.error('Please install podman and enable parallel')
        raise SystemExit()

    def podman_sync(self, repo, sync_root, work_root, log_root, arch):
        """
        This is for podman syncs

        Create sync_root/work/entries
        Generate scripts as needed into dir
        Each container runs their own script
        wait till all is finished
        """
        cmd = self.podman_cmd()
        contrunlist = []
        bad_exit_list = []
        self.log.info('Generating container entries')
        entries_dir = os.path.join(work_root, "entries")
        if not os.path.exists(entries_dir):
            os.makedirs(entries_dir, exist_ok=True)

        # yeah, I know.
        if not os.path.exists(log_root):
            os.makedirs(log_root, exist_ok=True)

        sync_single_arch = False
        arches_to_sync = self.arches
        if arch:
            sync_single_arch = True
            arches_to_sync = [arch]

        sync_single_repo = False
        repos_to_sync = self.repos
        if repo and not self.fullrun:
            sync_single_repo = True
            repos_to_sync = [repo]

        for r in repos_to_sync:
            entry_name_list = []
            repo_name = r
            arch_sync = arches_to_sync.copy()

            if r in self.repo_renames:
                repo_name = self.repo_renames[r]


            if 'all' in r and 'x86_64' in arches_to_sync and self.multilib:
                arch_sync.append('i686')

            # There should be a check here that if it's "all" and multilib
            # is on, i686 should get synced too.

            for a in arch_sync:
                entry_name = '{}-{}'.format(r, a)
                debug_entry_name = '{}-debug-{}'.format(r, a)

                entry_name_list.append(entry_name)

                if not self.ignore_debug:
                    entry_name_list.append(debug_entry_name)

                entry_point_sh = os.path.join(
                        entries_dir,
                        entry_name
                )

                debug_entry_point_sh = os.path.join(
                        entries_dir,
                        debug_entry_name
                )

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

                import_gpg_cmd = ("/usr/bin/rpm --import {}{}").format(
                        self.extra_files['git_raw_path'],
                        self.extra_files['gpg'][self.gpgkey]
                )

                arch_force_cp = ("/usr/bin/sed 's|$basearch|{}|g' {} > {}.{}".format(
                    a,
                    self.dnf_config,
                    self.dnf_config,
                    a
                ))

                sync_log = ("{}/{}-{}.log").format(
                        log_root,
                        repo_name,
                        a
                )

                debug_sync_log = ("{}/{}-{}-debug.log").format(
                        log_root,
                        repo_name,
                        a
                )

                sync_cmd = ("/usr/bin/dnf reposync -c {}.{} --download-metadata "
                        "--repoid={} -p {} --forcearch {} --norepopath "
                        "--gpgcheck 2>&1").format(
                        self.dnf_config,
                        a,
                        r,
                        os_sync_path,
                        a
                )

                debug_sync_cmd = ("/usr/bin/dnf reposync -c {}.{} "
                        "--download-metadata --repoid={}-debug -p {} --forcearch {} "
                        "--gpgcheck --norepopath 2>&1").format(
                        self.dnf_config,
                        a,
                        r,
                        debug_sync_path,
                        a
                )

                dnf_plugin_cmd = "/usr/bin/dnf install dnf-plugins-core -y"

                sync_template = self.tmplenv.get_template('reposync.tmpl')
                sync_output = sync_template.render(
                        import_gpg_cmd=import_gpg_cmd,
                        arch_force_cp=arch_force_cp,
                        dnf_plugin_cmd=dnf_plugin_cmd,
                        sync_cmd=sync_cmd,
                        sync_log=sync_log
                )

                debug_sync_template = self.tmplenv.get_template('reposync.tmpl')
                debug_sync_output = debug_sync_template.render(
                        import_gpg_cmd=import_gpg_cmd,
                        arch_force_cp=arch_force_cp,
                        dnf_plugin_cmd=dnf_plugin_cmd,
                        sync_cmd=debug_sync_cmd,
                        sync_log=debug_sync_log
                )

                entry_point_open = open(entry_point_sh, "w+")
                debug_entry_point_open = open(debug_entry_point_sh, "w+")

                entry_point_open.write(sync_output)
                debug_entry_point_open.write(debug_sync_output)

                entry_point_open.close()
                debug_entry_point_open.close()

                os.chmod(entry_point_sh, 0o755)
                os.chmod(debug_entry_point_sh, 0o755)

            # We ignoring sources?
            if not self.ignore_source:
                source_entry_name = '{}-source'.format(r)
                entry_name_list.append(source_entry_name)

                source_entry_point_sh = os.path.join(
                        entries_dir,
                        source_entry_name
                )

                source_sync_path = os.path.join(
                        sync_root,
                        repo_name,
                        'source/tree'
                )

                source_sync_log = ("{}/{}-source.log").format(
                        log_root,
                        repo_name
                )

                source_sync_cmd = ("/usr/bin/dnf reposync -c {} "
                        "--download-metadata --repoid={}-source -p {} "
                        "--gpgcheck --norepopath 2>&1").format(
                        self.dnf_config,
                        r,
                        source_sync_path
                )

                source_sync_template = self.tmplenv.get_template('reposync-src.tmpl')
                source_sync_output = source_sync_template.render(
                        import_gpg_cmd=import_gpg_cmd,
                        dnf_plugin_cmd=dnf_plugin_cmd,
                        sync_cmd=source_sync_cmd,
                        sync_log=source_sync_log
                )

                source_entry_point_open = open(source_entry_point_sh, "w+")
                source_entry_point_open.write(source_sync_output)
                source_entry_point_open.close()
                os.chmod(source_entry_point_sh, 0o755)

            # Spawn up all podman processes for repo
            self.log.info('Starting podman processes for %s ...' % r)

            #print(entry_name_list)
            for pod in entry_name_list:
                podman_cmd_entry = '{} run -d -it -v "{}:{}" -v "{}:{}" -v "{}:{}" --name {} --entrypoint {}/{} {}'.format(
                        cmd,
                        self.compose_root,
                        self.compose_root,
                        self.dnf_config,
                        self.dnf_config,
                        entries_dir,
                        entries_dir,
                        pod,
                        entries_dir,
                        pod,
                        self.container
                )
                #print(podman_cmd_entry)
                process = subprocess.call(
                        shlex.split(podman_cmd_entry),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                )

            join_all_pods = ' '.join(entry_name_list)
            time.sleep(3)
            self.log.info('Syncing %s ...' % r)
            pod_watcher = '{} wait {}'.format(
                    cmd,
                    join_all_pods
            )

            #print(pod_watcher)
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
            self.log.info('Syncing %s completed' % r)

        if len(bad_exit_list) > 0:
            self.log.error(
                    Color.BOLD + Color.RED + 'There were issues syncing these '
                    'repositories:' + Color.END
            )
            for issue in bad_exit_list:
                self.log.error(issue)
        else:
            self.log.info(
                    '[' + Color.BOLD + Color.GREEN + ' OK ' + Color.END + '] '
                    'No issues detected.'
            )

    def generate_compose_dirs(self) -> str:
        """
        Generate compose dirs for full runs
        """
        compose_base_dir = os.path.join(
                self.compose_base,
                "Rocky-{}-{}".format(self.fullversion, self.date_stamp)
        )
        self.log.info('Creating compose directory %s' % compose_base_dir)
        if not os.path.exists(compose_base_dir):
            os.makedirs(compose_base_dir)

        return compose_base_dir

    def symlink_to_latest(self, generated_dir):
        """
        Emulates pungi and symlinks latest-Rocky-X

        This link will be what is updated in full runs. Whatever is in this
        'latest' directory is what is rsynced on to staging after completion.
        This link should not change often.
        """
        try:
            os.remove(self.compose_latest_dir)
        except:
            pass

        self.log.info('Symlinking to latest-{}-{}...'.format(self.shortname, self.major_version))
        os.symlink(generated_dir, self.compose_latest_dir)

    def generate_conf(self, dest_path='/var/tmp') -> str:
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

        prehashed = ''
        if self.hashed:
            prehashed = "hashed-"
        # create dest_path
        if not os.path.exists(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        config_file = open(fname, "w+")
        repolist = []
        for repo in self.repos:

            constructed_url = '{}/{}/repo/{}{}/$basearch'.format(
                    self.repo_base_url,
                    self.project_id,
                    prehashed,
                    repo,
            )

            constructed_url_src = '{}/{}/repo/{}{}/src'.format(
                    self.repo_base_url,
                    self.project_id,
                    prehashed,
                    repo,
            )

            repodata = {
                    'name': repo,
                    'baseurl': constructed_url,
                    'srcbaseurl': constructed_url_src
            }
            repolist.append(repodata)

        template = self.tmplenv.get_template('repoconfig.tmpl')
        output = template.render(repos=repolist)
        config_file.write(output)

        config_file.close()
        return fname

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

    def repoclosure_work(self, sync_root, work_root, log_root):
        """
        This is where we run repoclosures, based on the configuration of each
        EL version. Each major version should have a dictionary of lists that
        point to which repos they'll be targetting. An empty list because the
        repoclosure is ran against itself, and itself only. In the case of 8,
        9, and perhaps 10, BaseOS is the only repo that should be checking
        against itself. (This means BaseOS should be able to survive by
        itself.)
        """
        cmd = self.podman_cmd()
        entries_dir = os.path.join(work_root, "entries")
        bad_exit_list = []

        if not self.parallel:
            self.log.error('repoclosure is too slow to run one by one. enable parallel mode.')
            raise SystemExit()

        self.log.info('Beginning repoclosure phase')
        for repo in self.repoclosure_map['repos']:
            if self.repo and repo not in self.repo:
                continue

            repoclosure_entry_name_list = []
            self.log.info('Setting up repoclosure for {}'.format(repo))

            for arch in self.repoclosure_map['arches']:
                repo_combination = []
                repoclosure_entry_name = 'repoclosure-{}-{}'.format(repo, arch)
                repoclosure_entry_name_list.append(repoclosure_entry_name)
                repoclosure_arch_list = self.repoclosure_map['arches'][arch]

                # Some repos will have additional repos to close against - this
                # helps append
                if len(self.repoclosure_map['repos'][repo]) > 0:
                    for l in self.repoclosure_map['repos'][repo]:
                        stretch = '--repofrompath={},file://{}/{}/{}/os --repo={}'.format(
                                l,
                                sync_root,
                                l,
                                arch,
                                l
                        )
                        repo_combination.append(stretch)

                join_repo_comb = ' '.join(repo_combination)

                repoclosure_entry_point_sh = os.path.join(
                        entries_dir,
                        repoclosure_entry_name
                )
                repoclosure_entry_point_sh = os.path.join(
                        entries_dir,
                        repoclosure_entry_name
                )
                repoclosure_cmd = ('/usr/bin/dnf repoclosure {} '
                        '--repofrompath={},file://{}/{}/{}/os --repo={} --check={} {} '
                        '| tee -a {}/{}-repoclosure-{}.log').format(
                        repoclosure_arch_list,
                        repo,
                        sync_root,
                        repo,
                        arch,
                        repo,
                        repo,
                        join_repo_comb,
                        log_root,
                        repo,
                        arch
                )
                repoclosure_entry_point_open = open(repoclosure_entry_point_sh, "w+")
                repoclosure_entry_point_open.write('#!/bin/bash\n')
                repoclosure_entry_point_open.write('set -o pipefail\n')
                repoclosure_entry_point_open.write('/usr/bin/dnf install dnf-plugins-core -y\n')
                repoclosure_entry_point_open.write('/usr/bin/dnf clean all\n')
                repoclosure_entry_point_open.write(repoclosure_cmd + '\n')
                repoclosure_entry_point_open.close()
                os.chmod(repoclosure_entry_point_sh, 0o755)
                repo_combination.clear()

            self.log.info('Spawning pods for %s' % repo)
            for pod in repoclosure_entry_name_list:
                podman_cmd_entry = '{} run -d -it -v "{}:{}" -v "{}:{}" -v "{}:{}" --name {} --entrypoint {}/{} {}'.format(
                        cmd,
                        self.compose_root,
                        self.compose_root,
                        self.dnf_config,
                        self.dnf_config,
                        entries_dir,
                        entries_dir,
                        pod,
                        entries_dir,
                        pod,
                        self.container
                )
                #print(podman_cmd_entry)
                process = subprocess.call(
                        shlex.split(podman_cmd_entry),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                )

            join_all_pods = ' '.join(repoclosure_entry_name_list)
            time.sleep(3)
            self.log.info('Performing repoclosure on %s ... ' % repo)
            pod_watcher = '{} wait {}'.format(
                    cmd,
                    join_all_pods
            )

            watch_man = subprocess.call(
                    shlex.split(pod_watcher),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
            )

            for pod in repoclosure_entry_name_list:
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

            repoclosure_entry_name_list.clear()
            self.log.info('Syncing %s completed' % repo)

        if len(bad_exit_list) > 0:
            self.log.error(
                    Color.BOLD + Color.RED + 'There were issues closing these '
                    'repositories:' + Color.END
            )
            for issue in bad_exit_list:
                self.log.error(issue)

    def deploy_extra_files(self):
        """
        deploys extra files based on info of rlvars including a
        extra_files.json

        also deploys COMPOSE_ID and maybe in the future a metadata dir with a
        bunch of compose-esque stuff.
        """
        self.log.info('Deploying extra files...')

class SigRepoSync:
    """
    This helps us do reposync operations for SIG's. Do not use this for the
    base system. Use RepoSync for that.
    """
    def __init__(
            self,
            rlvars,
            config,
            sigvars,
            major,
            repo=None,
            arch=None,
            ignore_source: bool = False,
            repoclosure: bool = False,
            skip_all: bool = False,
            hashed: bool = False,
            parallel: bool = False,
            dryrun: bool = False,
            fullrun: bool = False,
            nofail: bool = False,
            logger=None
        ):
        self.nofail = nofail
        self.dryrun = dryrun
        self.fullrun = fullrun
        self.arch = arch
        self.ignore_source = ignore_source
        self.skip_all = skip_all
        self.hashed = hashed
        self.repoclosure = repoclosure
        # Enables podman syncing, which should effectively speed up operations
        self.parallel = parallel
        # Relevant config items
        self.major_version = major
        self.date_stamp = config['date_stamp']
        self.repo_base_url = config['repo_base_url']
        self.compose_root = config['compose_root']
        self.compose_base = config['compose_root'] + "/" + major

        # Relevant major version items
        self.sigvars = sigvars
        self.sigrepos = sigvars.keys()
        #self.arches = sigvars['allowed_arches']
        #self.project_id = sigvars['project_id']
        self.sigrepo = repo

        # each el can have its own designated container to run stuff in,
        # otherwise we'll just default to the default config.
        self.container = config['container']
        if 'container' in rlvars and len(rlvars['container']) > 0:
            self.container = rlvars['container']

        if 'repoclosure_map' in rlvars and len(rlvars['repoclosure_map']) > 0:
            self.repoclosure_map = rlvars['repoclosure_map']

        self.staging_dir = os.path.join(
                    config['staging_root'],
                    config['sig_category_stub'],
                    major
        )

        self.compose_latest_dir = os.path.join(
                config['compose_root'],
                major,
                "latest-Rocky-{}-SIG".format(major)
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
            self.log = logging.getLogger("sigreposync")
            self.log.setLevel(logging.INFO)
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                    '%(asctime)s :: %(name)s :: %(message)s',
                    '%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.log.addHandler(handler)

        self.log.info('sig reposync init')
        self.log.info(major)
        #self.dnf_config = self.generate_conf()

    def run(self):
        """
        This runs the sig sync.
        """
        pass
