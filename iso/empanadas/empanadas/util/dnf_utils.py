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
import shutil
import time
import re
import json
import glob
#import pipes

from jinja2 import Environment, FileSystemLoader

import empanadas
from empanadas.common import Color, _rootdir
from empanadas.util import Shared

# initial treeinfo data is made here
import productmd.treeinfo

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
            refresh_extra_files: bool = False,
            refresh_treeinfo: bool = False,
            skip_all: bool = False,
            hashed: bool = False,
            parallel: bool = False,
            dryrun: bool = False,
            fullrun: bool = False,
            nofail: bool = False,
            gpgkey: str = 'stable',
            rlmode: str = 'stable',
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
        self.refresh_extra_files = refresh_extra_files
        self.refresh_treeinfo = refresh_treeinfo
        # Enables podman syncing, which should effectively speed up operations
        self.parallel = parallel
        # Relevant config items
        self.major_version = major
        self.date_stamp = config['date_stamp']
        self.timestamp = time.time()
        self.repo_base_url = config['repo_base_url']
        self.compose_root = config['compose_root']
        self.compose_base = config['compose_root'] + "/" + major
        self.profile = rlvars['profile']
        self.iso_map = rlvars['iso_map']
        self.distname = config['distname']
        self.fullname = rlvars['fullname']
        self.shortname = config['shortname']

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
        self.checksum = rlvars['checksum']

        self.compose_id = '{}-{}-{}'.format(
                config['shortname'],
                rlvars['revision'],
                config['date_stamp']
        )

        # Templates
        file_loader = FileSystemLoader(f"{_rootdir}/templates")
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
                "latest-{}-{}".format(
                    self.shortname,
                    self.profile
                )
        )

        self.compose_latest_sync = os.path.join(
                self.compose_latest_dir,
                "compose"
        )

        self.compose_log_dir = os.path.join(
                self.compose_latest_dir,
                "work/logs"
        )

        self.compose_global_work_root = os.path.join(
                self.compose_latest_dir,
                "work/global"
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

        # The repo name should be valid
        if self.repo is not None:
            if self.repo not in self.repos:
                self.log.error(Color.FAIL + 'Invalid repository: ' + self.repo)
                raise SystemExit()

    def run(self):
        """
        This must be called to perform the sync. This will run through, create
        the configuration file as required, and try to do a sync of every repo
        applicable or the repo actually specified. If self.repo is None, it
        will be assumed all repos are synced as dictated by rlvars.

         * Dry runs only create initial directories and structure
         * Full runs sync everything from the top and setup structure,
           including creating a symlink to latest-Rocky-X and creating the
           kickstart directories
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
            generated_dir = Shared.generate_compose_dirs(
                    self.compose_base,
                    self.shortname,
                    self.fullversion,
                    self.date_stamp,
                    self.log
            )
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

        global_work_root = os.path.join(
                work_root,
                "global",
        )

        if self.dryrun:
            self.log.error('Dry Runs are not supported just yet. Sorry!')
            raise SystemExit()

        if self.fullrun and self.refresh_extra_files:
            self.log.warn(Color.WARN + 'A full run implies extra files are also deployed.')

        self.sync(self.repo, sync_root, work_root, log_root, global_work_root, self.arch)

        if self.fullrun:
            self.deploy_extra_files(sync_root, global_work_root)
            self.deploy_treeinfo(self.repo, sync_root, self.arch)
            self.tweak_treeinfo(self.repo, sync_root, self.arch)
            self.symlink_to_latest(generated_dir)

        if self.repoclosure:
            self.repoclosure_work(sync_root, work_root, log_root)

        if self.refresh_extra_files and not self.fullrun:
            self.deploy_extra_files(sync_root, global_work_root)

        # deploy_treeinfo does NOT overwrite any treeinfo files. However,
        # tweak_treeinfo calls out to a method that does. This should not
        # cause issues as the method is fairly static in nature.
        if self.refresh_treeinfo and not self.fullrun:
            self.deploy_treeinfo(self.repo, sync_root, self.arch)
            self.tweak_treeinfo(self.repo, sync_root, self.arch)

        self.deploy_metadata(sync_root)

        self.log.info('Compose repo directory: %s' % sync_root)
        self.log.info('Compose logs: %s' % log_root)
        self.log.info('Compose completed.')

    def sync(self, repo, sync_root, work_root, log_root, global_work_root, arch=None):
        """
        Calls out syncing of the repos. We generally sync each component of a
        repo:
            * each architecture
            * each architecture debug
            * each source

        If parallel is true, we will run in podman.
        """
        if self.parallel:
            self.podman_sync(repo, sync_root, work_root, log_root, global_work_root, arch)
        else:
            self.dnf_sync(repo, sync_root, work_root, arch)

    def dnf_sync(self, repo, sync_root, work_root, arch):
        """
        This is for normal dnf syncs. This is very slow.
        """
        self.log.error('DNF syncing has been removed.')
        self.log.error('Please install podman and enable parallel')
        raise SystemExit()

    def podman_sync(
            self,
            repo,
            sync_root,
            work_root,
            log_root,
            global_work_root,
            arch
        ):
        """
        This is for podman syncs

        Create sync_root/work/entries
        Generate scripts as needed into dir
        Each container runs their own script
        wait till all is finished
        """
        cmd = Shared.podman_cmd(self.log)
        contrunlist = []
        bad_exit_list = []
        self.log.info('Generating container entries')
        entries_dir = os.path.join(work_root, "entries")
        if not os.path.exists(entries_dir):
            os.makedirs(entries_dir, exist_ok=True)

        # yeah, I know.
        if not os.path.exists(global_work_root):
            os.makedirs(global_work_root, exist_ok=True)

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

                if not self.ignore_debug and not a == 'source':
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
                        "--gpgcheck --assumeyes 2>&1").format(
                        self.dnf_config,
                        a,
                        r,
                        os_sync_path,
                        a
                )

                debug_sync_cmd = ("/usr/bin/dnf reposync -c {}.{} "
                        "--download-metadata --repoid={}-debug -p {} --forcearch {} "
                        "--gpgcheck --norepopath --assumeyes 2>&1").format(
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

                # During fullruns, a kickstart directory is made. Kickstart
                # should not be updated nor touched during regular runs under
                # any circumstances.
                if self.fullrun:
                    ks_entry_name = '{}-ks-{}'.format(r, a)
                    entry_name_list.append(ks_entry_name)
                    ks_point_sh = os.path.join(
                            entries_dir,
                            ks_entry_name
                    )

                    ks_sync_path = os.path.join(
                            sync_root,
                            repo_name,
                            a,
                            'kickstart'
                    )

                    ks_sync_cmd = ("/usr/bin/dnf reposync -c {}.{} --download-metadata "
                            "--repoid={} -p {} --forcearch {} --norepopath "
                            "--gpgcheck --assumeyes 2>&1").format(
                            self.dnf_config,
                            a,
                            r,
                            ks_sync_path,
                            a
                    )

                    ks_sync_log = ("{}/{}-{}-ks.log").format(
                            log_root,
                            repo_name,
                            a
                    )

                    ks_sync_template = self.tmplenv.get_template('reposync.tmpl')
                    ks_sync_output = ks_sync_template.render(
                            import_gpg_cmd=import_gpg_cmd,
                            arch_force_cp=arch_force_cp,
                            dnf_plugin_cmd=dnf_plugin_cmd,
                            sync_cmd=ks_sync_cmd,
                            sync_log=ks_sync_log
                    )
                    ks_entry_point_open = open(ks_point_sh, "w+")
                    ks_entry_point_open.write(ks_sync_output)
                    ks_entry_point_open.close()
                    os.chmod(ks_point_sh, 0o755)

            # We ignoring sources?
            if (not self.ignore_source and not arch) or (
                    not self.ignore_source and arch == 'source'):
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
                        "--gpgcheck --norepopath --assumeyes 2>&1").format(
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
            self.log.info(Color.INFO + 'Syncing ' + r + ' ...')
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
                    self.log.error(Color.FAIL + pod)
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
            self.log.info(Color.INFO + 'Syncing ' + r + ' completed')

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
                "{}-{}-config.repo".format(self.shortname, self.major_version)
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
                    'srcbaseurl': constructed_url_src,
                    'gpgkey': self.extra_files['git_raw_path'] + self.extra_files['gpg'][self.gpgkey]
            }
            repolist.append(repodata)

        template = self.tmplenv.get_template('repoconfig.tmpl')
        output = template.render(repos=repolist)
        config_file.write(output)

        config_file.close()
        return fname

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
        cmd = Shared.podman_cmd(self.log)
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
                    self.log.error(Color.FAIL + pod)
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

    def deploy_extra_files(self, sync_root, global_work_root):
        """
        deploys extra files based on info of rlvars including a
        extra_files.json

        might also deploy COMPOSE_ID and maybe in the future a metadata dir with
        a bunch of compose-esque stuff.
        """
        self.log.info(Color.INFO + 'Deploying treeinfo, discinfo, and media.repo')

        cmd = Shared.git_cmd(self.log)
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
                self.extra_files['git_repo'],
                self.extra_files['branch'],
                tmpclone
        )

        git_clone = subprocess.call(
                shlex.split(clonecmd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
        )

        self.log.info(Color.INFO + 'Deploying extra files to work and metadata directories ...')

        # Copy files to work root
        for extra in self.extra_files['list']:
            src = '/tmp/clone/' + extra
            # Copy extra files to root of compose here also - The extra files
            # are meant to be picked up by our ISO creation process and also
            # exist on our mirrors.
            try:
                shutil.copy2(src, extra_files_dir)
                shutil.copy2(src, metadata_dir)
            except:
                self.log.warn(Color.WARN + 'Extra file not copied: ' + src)

        try:
            shutil.rmtree(tmpclone)
        except OSError as e:
            self.log.error(Color.FAIL + 'Directory ' + tmpclone +
                    ' could not be removed: ' + e.strerror
            )

    def deploy_metadata(self, sync_root):
        """
        Deploys metadata that defines information about the compose. Some data
        will be close to how pungi produces it, but it won't be exact nor a
        perfect replica.
        """
        self.log.info(Color.INFO + 'Deploying metadata for this compose')
        # Create metadata here
        # Create COMPOSE_ID here (this doesn't necessarily match anything, it's
        # just an indicator)
        metadata_dir = os.path.join(
                sync_root,
                "metadata"
        )

        # It should already exist from a full run or refresh. This is just in
        # case and it doesn't hurt.
        if not os.path.exists(metadata_dir):
            os.makedirs(metadata_dir, exist_ok=True)

        with open(metadata_dir + '/COMPOSE_ID', "w+") as f:
            f.write(self.compose_id)
            f.close()

        Shared.write_metadata(
                self.timestamp,
                self.date_stamp,
                self.distname,
                self.fullversion,
                self.compose_id,
                metadata_dir + '/metadata'
        )

        # TODO: Add in each repo and their corresponding arch.
        productmd_date = self.date_stamp.split('.')[0]
        Shared.composeinfo_write(
                metadata_dir + '/composeinfo',
                self.distname,
                self.shortname,
                self.fullversion,
                'updates',
                productmd_date
        )

        self.log.info(Color.INFO + 'Metadata files phase completed.')

        # Deploy README to metadata directory
        readme_template = self.tmplenv.get_template('README.tmpl')
        readme_output = readme_template.render(
                fullname=self.fullname,
                version=empanadas.__version__
        )

        with open(metadata_dir + '/README', 'w+', encoding='utf-8') as readme_file:
            readme_file.write(readme_output)
            readme_file.close()


    def deploy_treeinfo(self, repo, sync_root, arch):
        """
        Deploys initial treeinfo files. These have the potential of being
        overwritten by our ISO process, which is fine. If there is a treeinfo
        found, it will be skipped.
        """
        self.log.info(Color.INFO + 'Deploying treeinfo, discinfo, and media.repo')

        arches_to_tree = self.arches
        if arch:
            arches_to_tree = [arch]

        repos_to_tree = self.repos
        if repo and not self.fullrun:
            repos_to_tree = [repo]

        # If a treeinfo or discinfo file exists, it should be skipped.
        for r in repos_to_tree:
            entry_name_list = []
            repo_name = r
            arch_tree = arches_to_tree.copy()

            if r in self.repo_renames:
                repo_name = self.repo_renames[r]

            # I feel it's necessary to make sure even i686 has .treeinfo and
            # .discinfo, just for consistency.
            if 'all' in r and 'x86_64' in arches_to_tree and self.multilib:
                arch_tree.append('i686')

            for a in arch_tree:
                if a == 'source':
                    continue

                os_tree_path = os.path.join(
                        sync_root,
                        repo_name,
                        a,
                        'os/.treeinfo'
                )

                os_disc_path = os.path.join(
                        sync_root,
                        repo_name,
                        a,
                        'os/.discinfo'
                )

                os_media_path = os.path.join(
                        sync_root,
                        repo_name,
                        a,
                        'os/media.repo'
                )

                ks_tree_path = os.path.join(
                        sync_root,
                        repo_name,
                        a,
                        'kickstart/.treeinfo'
                )

                ks_disc_path = os.path.join(
                        sync_root,
                        repo_name,
                        a,
                        'kickstart/.discinfo'
                )

                ks_media_path = os.path.join(
                        sync_root,
                        repo_name,
                        a,
                        'kickstart/media.repo'
                )


                if not os.path.exists(os_tree_path):
                    try:
                        Shared.treeinfo_new_write(
                                os_tree_path,
                                self.distname,
                                self.shortname,
                                self.fullversion,
                                a,
                                int(self.timestamp),
                                repo_name
                        )
                    except Exception as e:
                        self.log.error(Color.FAIL + repo_name + ' ' +
                                a + ' os .treeinfo could not be written'
                        )
                        self.log.error(e)
                else:
                    self.log.warn(Color.WARN + repo_name + ' ' + a + ' os .treeinfo already exists')

                if not os.path.exists(os_disc_path):
                    try:
                        Shared.discinfo_write(
                                self.timestamp,
                                self.fullname,
                                a,
                                os_disc_path
                        )
                    except Exception as e:
                        self.log.error(Color.FAIL + repo_name + ' ' +
                                a + ' os .discinfo could not be written'
                        )
                        self.log.error(e)
                else:
                    self.log.warn(Color.WARN + repo_name + ' ' + a +
                            ' os .discinfo already exists'
                    )

                if not os.path.exists(os_media_path):
                    try:
                        Shared.media_repo_write(
                                self.timestamp,
                                self.fullname,
                                os_media_path
                        )
                    except Exception as e:
                        self.log.error(Color.FAIL + repo_name + ' ' + a +
                                ' os media.repo could not be written'
                        )
                        self.log.error(e)
                else:
                    self.log.warn(Color.WARN + repo_name + ' ' + a +
                            ' os media.repo already exists'
                    )

                # Kickstart part of the repos
                if not os.path.exists(ks_tree_path):
                    try:
                        Shared.treeinfo_new_write(
                                ks_tree_path,
                                self.distname,
                                self.shortname,
                                self.fullversion,
                                a,
                                int(self.timestamp),
                                repo_name
                        )
                    except Exception as e:
                        self.log.error(Color.FAIL + repo_name + ' ' + a +
                                ' kickstart .treeinfo could not be written'
                        )
                        self.log.error(e)
                else:
                    self.log.warn(Color.WARN + repo_name + ' ' + a +
                            ' kickstart .treeinfo already exists'
                    )

                if not os.path.exists(ks_disc_path):
                    try:
                        Shared.discinfo_write(
                                self.timestamp,
                                self.fullname,
                                a,
                                ks_disc_path
                        )
                    except Exception as e:
                        self.log.error(Color.FAIL + repo_name + ' ' + a +
                                ' kickstart .discinfo could not be written'
                        )
                        self.log.error(e)
                else:
                    self.log.warn(Color.FAIL + repo_name + ' ' + a +
                            ' kickstart .discinfo already exists'
                    )

                if not os.path.exists(ks_media_path):
                    try:
                        Shared.media_repo_write(
                                self.timestamp,
                                self.fullname,
                                ks_media_path
                        )
                    except Exception as e:
                        self.log.error(Color.FAIL + repo_name + ' ' + a +
                                ' kickstart media.repo could not be written'
                        )
                        self.log.error(e)
                else:
                    self.log.warn(Color.WARN + repo_name + ' ' + a +
                            ' kickstart media.repo already exists'
                    )

                if not self.ignore_debug and not a == 'source':
                    debug_tree_path = os.path.join(
                            sync_root,
                            repo_name,
                            a,
                            'debug/tree/.treeinfo'
                    )

                    debug_disc_path = os.path.join(
                            sync_root,
                            repo_name,
                            a,
                            'debug/tree/.discinfo'
                    )

                    debug_media_path = os.path.join(
                            sync_root,
                            repo_name,
                            a,
                            'debug/tree/media.repo'
                    )

                    if not os.path.exists(debug_tree_path):
                        try:
                            Shared.treeinfo_new_write(
                                    debug_tree_path,
                                    self.distname,
                                    self.shortname,
                                    self.fullversion,
                                    a,
                                    self.timestamp,
                                    repo_name
                            )
                        except Exception as e:
                            self.log.error(Color.FAIL + repo_name + ' ' + a +
                                    ' debug .treeinfo could not be written'
                            )
                            self.log.error(e)
                    else:
                        self.log.warn(Color.WARN + r + ' ' + a +
                                ' debug .treeinfo already exists'
                        )

                    if not os.path.exists(debug_disc_path):
                        try:
                            Shared.discinfo_write(
                                    self.timestamp,
                                    self.fullname,
                                    a,
                                    debug_disc_path
                            )
                        except Exception as e:
                            self.log.error(Color.FAIL + repo_name + ' ' + a +
                                    ' debug .discinfo could not be written'
                            )
                            self.log.error(e)
                    else:
                        self.log.warn(Color.WARN + r + ' ' + a +
                                ' debug .discinfo already exists'
                        )

                    if not os.path.exists(debug_media_path):
                        try:
                            Shared.media_repo_write(
                                    self.timestamp,
                                    self.fullname,
                                    debug_media_path
                            )
                        except Exception as e:
                            self.log.error(Color.FAIL + repo_name + ' ' + a +
                                    ' debug media.repo could not be written'
                            )
                            self.log.error(e)
                    else:
                        self.log.warn(Color.WARN + repo_name + ' ' + a +
                                ' debug media.repo already exists'
                        )


            if not self.ignore_source and not arch:
                source_tree_path = os.path.join(
                        sync_root,
                        repo_name,
                        'source/tree/.treeinfo'
                )

                source_disc_path = os.path.join(
                        sync_root,
                        repo_name,
                        'source/tree/.discinfo'
                )

                source_media_path = os.path.join(
                        sync_root,
                        repo_name,
                        'source/tree/media.repo'
                )

                if not os.path.exists(source_tree_path):
                    try:
                        Shared.treeinfo_new_write(
                                source_tree_path,
                                self.distname,
                                self.shortname,
                                self.fullversion,
                                'src',
                                self.timestamp,
                                repo_name
                        )
                    except Exception as e:
                        self.log.error(Color.FAIL + repo_name + ' source os .treeinfo could not be written')
                        self.log.error(e)
                else:
                    self.log.warn(Color.WARN + repo_name + ' source os .treeinfo already exists')

                if not os.path.exists(source_disc_path):
                    try:
                        Shared.discinfo_write(
                                self.timestamp,
                                self.fullname,
                                'src',
                                source_disc_path
                        )
                    except Exception as e:
                        self.log.error(Color.FAIL + repo_name + ' source os .discinfo could not be written')
                        self.log.error(e)
                else:
                    self.log.warn(Color.WARN + repo_name + ' source .discinfo already exists')

                if not os.path.exists(source_media_path):
                    try:
                        Shared.media_repo_write(
                                self.timestamp,
                                self.fullname,
                                source_media_path
                        )
                    except Exception as e:
                        self.log.error(Color.FAIL + repo_name + ' source os media.repo could not be written')
                        self.log.error(e)
                else:
                    self.log.warn(Color.WARN + repo_name + ' source media.repo already exists')

    def tweak_treeinfo(self, repo, sync_root, arch):
        """
        This modifies treeinfo for the primary repository. If the repository is
        listed in the iso_map as a non-disc, it will be considered for modification.
        """
        variants_to_tweak = []

        arches_to_tree = self.arches
        if arch:
            arches_to_tree = [arch]

        repos_to_tree = self.repos
        if repo and not self.fullrun:
            repos_to_tree = [repo]

        for r in repos_to_tree:
            entry_name_list = []
            repo_name = r
            arch_tree = arches_to_tree.copy()

            if r in self.iso_map['images']:
                variants_to_tweak.append(r)

        if not len(variants_to_tweak) > 0:
            self.log.info(Color.INFO + 'No treeinfo to tweak.')
            return

        for a in arches_to_tree:
            for v in variants_to_tweak:
                self.log.info(Color.INFO + 'Tweaking treeinfo for ' + a + ' ' + v)
                image = os.path.join(sync_root, v, a, 'os')
                imagemap = self.iso_map['images'][v]
                data = {
                        'arch': a,
                        'variant': v,
                        'variant_path': image,
                        'checksum': self.checksum,
                        'distname': self.distname,
                        'fullname': self.fullname,
                        'shortname': self.shortname,
                        'release': self.fullversion,
                        'timestamp': self.timestamp,
                }

                try:
                    Shared.treeinfo_modify_write(data, imagemap, self.log)
                except Exception as e:
                    self.log.error(Color.FAIL + 'There was an error writing os treeinfo.')
                    self.log.error(e)

                if self.fullrun:
                    ksimage = os.path.join(sync_root, v, a, 'kickstart')
                    ksdata = {
                            'arch': a,
                            'variant': v,
                            'variant_path': ksimage,
                            'checksum': self.checksum,
                            'distname': self.distname,
                            'fullname': self.fullname,
                            'shortname': self.shortname,
                            'release': self.fullversion,
                            'timestamp': self.timestamp,
                    }

                    try:
                        Shared.treeinfo_modify_write(ksdata, imagemap, self.log)
                    except Exception as e:
                        self.log.error(Color.FAIL + 'There was an error writing kickstart treeinfo.')
                        self.log.error(e)

    def run_compose_closeout(self):
        """
        Closes out a compose. This ensures the ISO's are synced from work/isos
        to compose/isos, checks for live media and syncs as well from work/live
        to compose/live, deploys final metadata.
        """
        # latest-X-Y should exist at all times for this to work.
        work_root = os.path.join(
                self.compose_latest_dir,
                'work'
        )
        sync_root = self.compose_latest_sync

        sync_iso_root = os.path.join(
                sync_root,
                'isos'
        )

        tmp_dir = os.path.join(
                self.compose_root,
                'partitions'
        )

        # Verify if the link even exists
        if not os.path.exists(self.compose_latest_dir):
            self.log.error(
                    '!! Latest compose link is broken does not exist: %s' % self.compose_latest_dir
            )
            self.log.error(
                    '!! Please perform a full run if you have not done so.'
            )
            raise SystemExit()

        log_root = os.path.join(
                work_root,
                "logs",
                self.date_stamp
        )

        iso_root = os.path.join(
                work_root,
                "isos"
        )

        live_root = os.path.join(
                work_root,
                "live"
        )

        sync_live_root = os.path.join(
                sync_root,
                'live'
        )

        images_root = os.path.join(
                work_root,
                'images'
        )

        sync_images_root = os.path.join(
                sync_root,
                'images'
        )

        global_work_root = os.path.join(
                work_root,
                "global",
        )

        # Standard ISOs
        self.log.info(Color.INFO + 'Starting to sync ISOs to compose')

        if os.path.exists('/usr/bin/fpsync'):
            self.log.info(Color.INFO + 'Starting up fpsync')
            message, ret = Shared.fpsync_method(iso_root, sync_iso_root, tmp_dir)
        elif os.path.exists('/usr/bin/parallel') and os.path.exists('/usr/bin/rsync'):
            self.log.info(Color.INFO + 'Starting up parallel | rsync')
            message, ret = Shared.rsync_method(iso_root, sync_iso_root)
        else:
            self.log.error(
                    Color.FAIL +
                    'fpsync nor parallel + rsync were found on this system. ' +
                    'There is also no built-in parallel rsync method at this ' +
                    'time.'
            )
            raise SystemExit()

        if ret != 0:
            self.log.error(Color.FAIL + message)
        else:
            self.log.info(Color.INFO + message)

        # Live images
        if os.path.exists(live_root):
            self.log.info(Color.INFO + 'Starting to sync live images to compose')

            if os.path.exists('/usr/bin/fpsync'):
                message, ret = Shared.fpsync_method(live_root, sync_live_root, tmp_dir)
            elif os.path.exists('/usr/bin/parallel') and os.path.exists('/usr/bin/rsync'):
                message, ret = Shared.rsync_method(live_root, sync_live_root)

            if ret != 0:
                self.log.error(Color.FAIL + message)
            else:
                self.log.info(Color.INFO + message)

        # Cloud images
        if os.path.exists(images_root):
            self.log.info(Color.INFO + 'Starting to sync cloud images to compose')

            if os.path.exists('/usr/bin/fpsync'):
                message, ret = Shared.fpsync_method(images_root, sync_images_root, tmp_dir)
            elif os.path.exists('/usr/bin/parallel') and os.path.exists('/usr/bin/rsync'):
                message, ret = Shared.rsync_method(images_root, sync_images_root)

            if ret != 0:
                self.log.error(Color.FAIL + message)
            else:
                self.log.info(Color.INFO + message)

        # Combine all checksums here
        for arch in self.arches:
            iso_arch_root = os.path.join(sync_iso_root, arch)
            iso_arch_checksum = os.path.join(iso_arch_root, 'CHECKSUM')
            if os.path.exists(iso_arch_root):
                with open(iso_arch_checksum, 'w+', encoding='utf-8') as fp:
                    for check in glob.iglob(iso_arch_root + '/*.CHECKSUM'):
                        with open(check, 'r', encoding='utf-8') as sum:
                            for line in sum:
                                fp.write(line)
                            sum.close()
                    fp.close()

            live_arch_root = os.path.join(sync_live_root, arch)
            live_arch_checksum = os.path.join(live_arch_root, 'CHECKSUM')
            if os.path.exists(live_arch_root):
                with open(live_arch_checksum, 'w+', encoding='utf-8') as lp:
                    for lcheck in glob.iglob(live_arch_root + '/*.CHECKSUM'):
                        with open(lcheck, 'r', encoding='utf-8') as sum:
                            for line in sum:
                                lp.write(line)
                            sum.close()
                    lp.close()

            images_arch_root = os.path.join(sync_images_root, arch)
            images_arch_checksum = os.path.join(sync_images_root, 'CHECKSUM')
            if os.path.exists(images_arch_root):
                with open(images_arch_checksum, 'w+', encoding='utf-8') as ip:
                    for icheck in glob.iglob(images_arch_root + '/*.CHECKSUM'):
                        with open(icheck, 'r', encoding='utf-8') as sum:
                            for line in sum:
                                ip.write(line)
                            sum.close()
                    ip.close()

        # Deploy final metadata for a close out
        self.deploy_metadata(sync_root)

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
            ignore_debug: bool = False,
            ignore_source: bool = False,
            repoclosure: bool = False,
            refresh_extra_files: bool = False,
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
        self.ignore_debug = ignore_debug
        self.ignore_source = ignore_source
        self.skip_all = skip_all
        self.hashed = hashed
        self.repoclosure = repoclosure
        self.refresh_extra_files = refresh_extra_files
        # Enables podman syncing, which should effectively speed up operations
        self.parallel = parallel
        # Relevant config items
        self.major_version = major
        self.date_stamp = config['date_stamp']
        self.timestamp = time.time()
        self.repo_base_url = config['repo_base_url']
        self.compose_root = config['compose_root']
        self.compose_base = config['compose_root'] + "/" + major
        self.profile = rlvars['profile']
        self.sigprofile = sigvars['profile']
        self.iso_map = rlvars['iso_map']
        self.distname = config['distname']
        self.fullname = rlvars['fullname']
        self.shortname = config['shortname']

        # Relevant major version items
        self.sigvars = sigvars
        self.sigrepos = sigvars.keys()
        #self.arches = sigvars['allowed_arches']
        #self.project_id = sigvars['project_id']
        self.sigrepo = repo

        # Templates
        file_loader = FileSystemLoader(f"{_rootdir}/templates")
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
                    config['sig_category_stub'],
                    major
        )

        self.compose_latest_dir = os.path.join(
                config['compose_root'],
                major,
                "latest-{}-{}-SIG-{}".format(
                    self.shortname,
                    major,
                    self.sigprofile
                )
        )

        self.compose_latest_sync = os.path.join(
                self.compose_latest_dir,
                "compose"
        )

        self.compose_log_dir = os.path.join(
                self.compose_latest_dir,
                "work/logs"
        )

        self.compose_global_work_root = os.path.join(
                self.compose_latest_dir,
                "work/global"
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
        #self.dnf_config = Shared.generate_conf()

    def run(self):
        """
        This runs the sig sync.
        """
        pass
