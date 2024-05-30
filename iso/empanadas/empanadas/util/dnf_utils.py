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
            gpg_check: bool = True,
            repo_gpg_check: bool = True,
            rlmode: str = 'stable',
            just_pull_everything: bool = False,
            extra_dnf_args=None,
            reposync_clean_old: bool = False,
            fpsync: bool = False,
            logger=None,
            log_level='INFO',
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
        self.fpsync = fpsync
        # Enables podman syncing, which should effectively speed up operations
        self.parallel = parallel
        # This makes it so every repo is synced at the same time.
        # This is EXTREMELY dangerous.
        self.just_pull_everything = just_pull_everything
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
        self.revision_level = rlvars['revision'] + "-" + rlvars['rclvl']
        self.revision = rlvars['revision']
        self.fullversion = rlvars['revision']
        self.arches = rlvars['allowed_arches']
        self.project_id = rlvars['project_id']
        self.repo_renames = rlvars['renames']
        self.repos = rlvars['all_repos']
        self.multilib = rlvars['provide_multilib']
        self.repo = repo
        self.extra_files = rlvars['extra_files']
        self.gpgkey = rlvars['gpg_key']
        if rlvars['repo_gpg_key']:
            self.gpgkey = rlvars['gpg_key'] + rlvars['repo_gpg_key']
        self.checksum = rlvars['checksum']
        self.gpg_check = gpg_check
        self.repo_gpg_check = repo_gpg_check

        self.compose_id = '{}-{}-{}'.format(
                config['shortname'],
                rlvars['revision'],
                config['date_stamp']
        )

        # Templates
        file_loader = FileSystemLoader(f"{_rootdir}/templates")
        self.tmplenv = Environment(loader=file_loader)

        # dnf args
        dnf_args_to_add = []
        if extra_dnf_args:
            if '--delete' in extra_dnf_args:
                raise SystemExit('Please use the --reposync-clean option instead.')

            dnf_args_to_add.extend(extra_dnf_args.split(' '))

        self.extra_dnf_args = dnf_args_to_add.copy()
        self.reposync_clean_old = reposync_clean_old

        # each el can have its own designated container to run stuff in,
        # otherwise we'll just default to the default config.
        self.container = config['container']
        if 'container' in rlvars and len(rlvars['container']) > 0:
            self.container = rlvars['container']

        if 'repoclosure_map' in rlvars and len(rlvars['repoclosure_map']) > 0:
            self.repoclosure_map = rlvars['repoclosure_map']

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
        self.log.info(self.revision_level)

        # The repo name should be valid
        if self.repo is not None:
            bad_repo_list = []
            repo_list_if_commas = self.repo.split(',')
            for repoitem in repo_list_if_commas:
                if repoitem not in self.repos:
                    bad_repo_list.append(repoitem)

            if len(bad_repo_list) > 0:
                self.log.error(
                        Color.BOLD + Color.RED + 'These repos are not listed:' + Color.END
                )
                for badrepo in bad_repo_list:
                    self.log.error(badrepo)
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

        self.dnf_config = Shared.generate_conf(
                self.shortname,
                self.major_version,
                self.repos,
                self.repo_base_url,
                self.project_id,
                self.hashed,
                self.extra_files,
                self.gpgkey,
                self.gpg_check,
                self.repo_gpg_check,
                self.tmplenv,
                self.log
        )

        if self.dryrun:
            self.log.error('Dry Runs are not supported just yet. Sorry!')
            raise SystemExit()

        if self.fullrun and self.refresh_extra_files:
            self.log.warning(Color.WARN + 'A full run implies extra files are also deployed.')

        if not self.skip_all:
            self.sync(self.repo, sync_root, work_root, log_root, global_work_root, self.arch)

        if self.fullrun:
            Shared.deploy_extra_files(self.extra_files, sync_root, global_work_root, self.log)
            self.deploy_treeinfo(self.repo, sync_root, self.arch)
            self.tweak_treeinfo(self.repo, sync_root, self.arch)
            #self.symlink_to_latest(generated_dir)
            Shared.symlink_to_latest(self.shortname, self.major_version,
                    generated_dir, self.compose_latest_dir, self.log)

        if self.repoclosure:
            self.repoclosure_work(sync_root, work_root, log_root)

        if self.refresh_extra_files and not self.fullrun:
            Shared.deploy_extra_files(self.extra_files, sync_root, global_work_root, self.log)

        # deploy_treeinfo does NOT overwrite any treeinfo files. However,
        # tweak_treeinfo calls out to a method that does. This should not
        # cause issues as the method is fairly static in nature.
        if self.refresh_treeinfo and not self.fullrun:
            self.deploy_treeinfo(self.repo, sync_root, self.arch, refresh=True)
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
            Shared.norm_dnf_sync(self, repo, sync_root, work_root, arch, self.log)

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
        extra_dnf_args = ' '.join(self.extra_dnf_args.copy())
        reposync_delete = '--delete' if self.reposync_clean_old else ''
        self.log.info('Generating container entries')
        entries_dir = os.path.join(work_root, "entries")
        if not os.path.exists(entries_dir):
            os.makedirs(entries_dir, exist_ok=True)

        # yeah, I know.
        if not os.path.exists(global_work_root):
            os.makedirs(global_work_root, exist_ok=True)

        if not os.path.exists(log_root):
            os.makedirs(log_root, exist_ok=True)

        arches_to_sync = self.arches
        if arch:
            arches_to_sync = arch.split(',')

        repos_to_sync = self.repos
        if repo and not self.fullrun:
            repos_to_sync = repo.split(',')

        for r in repos_to_sync:
            entry_name_list = []
            repo_name = r
            arch_sync = arches_to_sync.copy()

            if r in self.repo_renames:
                repo_name = self.repo_renames[r]

            # Sync all if arch is x86_64 and multilib is true
            if 'all' in r and 'x86_64' in arches_to_sync and self.multilib:
                arch_sync.append('i686')

            for a in arch_sync:
                entry_name = f'{r}-{a}'
                debug_entry_name = f'{r}-debug-{a}'

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

                gpg_key_list = self.gpgkey
                import_gpg_cmd = f"/usr/bin/rpm --import"
                arch_force_cp = f"/usr/bin/sed 's|$basearch|{a}|g' "\
                        f"{self.dnf_config} > {self.dnf_config}.{a}"

                sync_log = f"{log_root}/{repo_name}-{a}.log"
                debug_sync_log = f"{log_root}/{repo_name}-{a}-debug.log"
                metadata_cmd = f"/usr/bin/dnf makecache -c {self.dnf_config}.{a} --repoid={r} "\
                        f"--forcearch {a} --assumeyes 2>&1"

                sync_cmd = f"/usr/bin/dnf reposync -c {self.dnf_config}.{a} --download-metadata "\
                        f"--repoid={r} -p {os_sync_path} --forcearch {a} --norepopath "\
                        f"--remote-time --gpgcheck --assumeyes {reposync_delete} 2>&1"

                debug_metadata_cmd = f"/usr/bin/dnf makecache -c {self.dnf_config}.{a} "\
                        f"--repoid={r}-debug --forcearch {a} --assumeyes 2>&1"

                debug_sync_cmd = f"/usr/bin/dnf reposync -c {self.dnf_config}.{a} "\
                        f"--download-metadata --repoid={r}-debug -p {debug_sync_path} "\
                        f"--forcearch {a} --gpgcheck --norepopath --remote-time "\
                        f"--assumeyes {reposync_delete} 2>&1"

                dnf_plugin_cmd = "/usr/bin/dnf install dnf-plugins-core -y"

                sync_template = self.tmplenv.get_template('reposync.tmpl')
                sync_output = sync_template.render(
                        gpg_key_list=gpg_key_list,
                        import_gpg_cmd=import_gpg_cmd,
                        arch_force_cp=arch_force_cp,
                        dnf_plugin_cmd=dnf_plugin_cmd,
                        sync_cmd=sync_cmd,
                        metadata_cmd=metadata_cmd,
                        sync_log=sync_log,
                        download_path=os_sync_path
                )

                debug_sync_template = self.tmplenv.get_template('reposync.tmpl')
                debug_sync_output = debug_sync_template.render(
                        gpg_key_list=gpg_key_list,
                        import_gpg_cmd=import_gpg_cmd,
                        arch_force_cp=arch_force_cp,
                        dnf_plugin_cmd=dnf_plugin_cmd,
                        sync_cmd=debug_sync_cmd,
                        metadata_cmd=debug_metadata_cmd,
                        sync_log=debug_sync_log,
                        download_path=debug_sync_path
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
                    ks_entry_name = f'{r}-ks-{a}'
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

                    ks_metadata_cmd = f"/usr/bin/dnf makecache -c {self.dnf_config}.{a} "\
                            f"--repoid={r} --forcearch {a} --assumeyes 2>&1"

                    ks_sync_cmd = f"/usr/bin/dnf reposync -c {self.dnf_config}.{a} --download-metadata "\
                            f"--repoid={r} -p {ks_sync_path} --forcearch {a} --norepopath "\
                            "--gpgcheck --assumeyes --remote-time 2>&1"

                    ks_sync_log = f"{log_root}/{repo_name}-{a}-ks.log"

                    ks_sync_template = self.tmplenv.get_template('reposync.tmpl')
                    ks_sync_output = ks_sync_template.render(
                            gpg_key_list=gpg_key_list,
                            import_gpg_cmd=import_gpg_cmd,
                            arch_force_cp=arch_force_cp,
                            dnf_plugin_cmd=dnf_plugin_cmd,
                            sync_cmd=ks_sync_cmd,
                            metadata_cmd=ks_metadata_cmd,
                            sync_log=ks_sync_log
                    )
                    ks_entry_point_open = open(ks_point_sh, "w+")
                    ks_entry_point_open.write(ks_sync_output)
                    ks_entry_point_open.close()
                    os.chmod(ks_point_sh, 0o755)

            # We ignoring sources?
            if (not self.ignore_source and not arch) or (
                    not self.ignore_source and arch == 'source'):
                source_entry_name = f'{r}-source'
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

                source_sync_log = f"{log_root}/{repo_name}-source.log"

                source_metadata_cmd = f"/usr/bin/dnf makecache -c {self.dnf_config} "\
                        f"--repoid={r}-source --assumeyes 2>&1"

                source_sync_cmd = f"/usr/bin/dnf reposync -c {self.dnf_config} "\
                        f"--download-metadata --repoid={r}-source -p {source_sync_path} "\
                        f"--gpgcheck --norepopath --remote-time --assumeyes {reposync_delete} 2>&1"

                source_sync_template = self.tmplenv.get_template('reposync-src.tmpl')
                source_sync_output = source_sync_template.render(
                        gpg_key_list=gpg_key_list,
                        import_gpg_cmd=import_gpg_cmd,
                        dnf_plugin_cmd=dnf_plugin_cmd,
                        sync_cmd=source_sync_cmd,
                        metadata_cmd=source_metadata_cmd,
                        sync_log=source_sync_log
                )

                source_entry_point_open = open(source_entry_point_sh, "w+")
                source_entry_point_open.write(source_sync_output)
                source_entry_point_open.close()
                os.chmod(source_entry_point_sh, 0o755)

            # Spawn up all podman processes for repo
            self.log.info(Color.INFO + 'Starting podman processes for %s ...' % r)

            #print(entry_name_list)
            for pod in entry_name_list:
                podman_cmd_entry = '{} run -d -it -v "{}:{}" -v "{}:{}:z" -v "{}:{}" --name {} --entrypoint {}/{} {}'.format(
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
            self.log.info(Color.INFO + 'Arches: ' + ' '.join(arch_sync))
            pod_watcher = f'{cmd} wait {join_all_pods}'

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
                repoclosure_entry_name = f'repoclosure-{repo}-{arch}'
                repoclosure_entry_name_list.append(repoclosure_entry_name)
                repoclosure_arch_list = self.repoclosure_map['arches'][arch]

                # Some repos will have additional repos to close against - this
                # helps append
                if len(self.repoclosure_map['repos'][repo]) > 0:
                    for l in self.repoclosure_map['repos'][repo]:
                        stretch = f'--repofrompath={l},file://{sync_root}/{l}/{arch}/os '\
                                f'--repo={l}'
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

                with open(repoclosure_entry_point_sh, "w+") as rcep:
                    rcep.write('#!/bin/bash\n')
                    rcep.write('set -o pipefail\n')
                    rcep.write('/usr/bin/dnf install dnf-plugins-core -y\n')
                    rcep.write('/usr/bin/dnf clean all\n')
                    rcep.write(repoclosure_cmd + '\n')
                    rcep.close()

                os.chmod(repoclosure_entry_point_sh, 0o755)
                repo_combination.clear()

            self.log.info('Spawning pods for %s' % repo)
            for pod in repoclosure_entry_name_list:
                podman_cmd_entry = '{} run -d -it -v "{}:{}" -v "{}:{}:z" -v "{}:{}" --name {} --entrypoint {}/{} {}'.format(
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
            pod_watcher = f'{cmd} wait {join_all_pods}'

            watch_man = subprocess.call(
                    shlex.split(pod_watcher),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
            )

            for pod in repoclosure_entry_name_list:
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

            repoclosure_entry_name_list.clear()
            self.log.info('Syncing %s completed' % repo)

        if len(bad_exit_list) > 0:
            self.log.error(
                    Color.BOLD + Color.RED + 'There were issues closing these '
                    'repositories:' + Color.END
            )
            for issue in bad_exit_list:
                self.log.error(issue)

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
                sync_root,
                self.distname,
                self.shortname,
                self.fullversion,
                'updates',
                productmd_date,
                self.arches,
                self.repos
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


    def deploy_treeinfo(self, repo, sync_root, arch, refresh=False):
        """
        Deploys initial treeinfo files. These have the potential of being
        overwritten by our ISO process, which is fine. If there is a treeinfo
        found, it will be skipped.
        """
        self.log.info(Color.INFO + 'Deploying treeinfo, discinfo, and media.repo')

        arches_to_tree = self.arches
        if arch:
            arches_to_tree = arch.split(',')

        repos_to_tree = self.repos
        if repo and not self.fullrun:
            repos_to_tree = repo.split(',')

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

                if not os.path.exists(os_tree_path) or (os.path.exists(os_tree_path) and refresh):
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
                    self.log.warning(Color.WARN + repo_name + ' ' + a + ' os .treeinfo already exists')

                if not os.path.exists(os_disc_path) or (os.path.exists(os_disc_path) and refresh):
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
                    self.log.warning(Color.WARN + repo_name + ' ' + a +
                            ' os .discinfo already exists'
                    )

                if not os.path.exists(os_media_path) or (os.path.exists(os_media_path) and refresh):
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
                    self.log.warning(Color.WARN + repo_name + ' ' + a +
                            ' os media.repo already exists'
                    )

                # Kickstart part of the repos
                if not os.path.exists(ks_tree_path) or (os.path.exists(ks_tree_path) and refresh):
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
                    self.log.warning(Color.WARN + repo_name + ' ' + a +
                            ' kickstart .treeinfo already exists'
                    )

                if not os.path.exists(ks_disc_path) or (os.path.exists(ks_disc_path) and refresh):
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
                    self.log.warning(Color.FAIL + repo_name + ' ' + a +
                            ' kickstart .discinfo already exists'
                    )

                if not os.path.exists(ks_media_path) or (os.path.exists(ks_media_path) and refresh):
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
                    self.log.warning(Color.WARN + repo_name + ' ' + a +
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

                    if not os.path.exists(debug_tree_path) or (os.path.exists(debug_tree_path) and refresh):
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
                        self.log.warning(Color.WARN + r + ' ' + a +
                                ' debug .treeinfo already exists'
                        )

                    if not os.path.exists(debug_disc_path) or (os.path.exists(debug_disc_path) and refresh):
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
                        self.log.warning(Color.WARN + r + ' ' + a +
                                ' debug .discinfo already exists'
                        )

                    if not os.path.exists(debug_media_path) or (os.path.exists(debug_media_path) and refresh):
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
                        self.log.warning(Color.WARN + repo_name + ' ' + a +
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

                if not os.path.exists(source_tree_path) or (os.path.exists(source_tree_path) and refresh):
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
                    self.log.warning(Color.WARN + repo_name + ' source os .treeinfo already exists')

                if not os.path.exists(source_disc_path) or (os.path.exists(source_disc_path) and refresh):
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
                    self.log.warning(Color.WARN + repo_name + ' source .discinfo already exists')

                if not os.path.exists(source_media_path) or (os.path.exists(source_media_path) and refresh):
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
                    self.log.warning(Color.WARN + repo_name + ' source media.repo already exists')

    def tweak_treeinfo(self, repo, sync_root, arch):
        """
        This modifies treeinfo for the primary repository. If the repository is
        listed in the iso_map as a non-disc, it will be considered for modification.
        """
        variants_to_tweak = []

        arches_to_tree = self.arches
        if arch:
            arches_to_tree = arch.split(',')

        repos_to_tree = self.repos
        if repo and not self.fullrun:
            repos_to_tree = repo.split(',')

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

                #if self.fullrun:
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

    def refresh_compose_treeinfo(self):
        """
        It is rare that this should be called.
        """
        sync_root = self.compose_latest_sync
        self.deploy_treeinfo(self.repo, sync_root, self.arch, refresh=True)
        self.tweak_treeinfo(self.repo, sync_root, self.arch)

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

        if os.path.exists('/usr/bin/fpsync') and self.fpsync:
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

            if os.path.exists('/usr/bin/fpsync') and self.fpsync:
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

            if os.path.exists('/usr/bin/fpsync') and self.fpsync:
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
            images_arch_checksum = os.path.join(images_arch_root, 'CHECKSUM')
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

    def run_upstream_repoclosure(self):
        """
        This does a repoclosure check in peridot
        """
        work_root = os.path.join(
                self.compose_latest_dir,
                'work'
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

        if not os.path.exists(log_root):
            os.makedirs(log_root, exist_ok=True)

        cmd = Shared.podman_cmd(self.log)
        entries_dir = os.path.join(work_root, "entries")
        bad_exit_list = []
        dnf_config = Shared.generate_conf(
                self.shortname,
                self.major_version,
                self.repos,
                self.repo_base_url,
                self.project_id,
                self.hashed,
                self.extra_files,
                self.gpgkey,
                self.gpg_check,
                self.repo_gpg_check,
                self.tmplenv,
                self.log
        )


        if not self.parallel:
            self.log.error('repoclosure is too slow to run one by one. enable parallel mode.')
            raise SystemExit()

        self.log.info('Beginning upstream repoclosure')
        for repo in self.repoclosure_map['repos']:
            if self.repo and repo not in self.repo:
                continue

            repoclosure_entry_name_list = []
            self.log.info('Setting up repoclosure for {}'.format(repo))

            for arch in self.repoclosure_map['arches']:
                repo_combination = []
                repoclosure_entry_name = f'peridot-repoclosure-{repo}-{arch}'
                repoclosure_entry_name_list.append(repoclosure_entry_name)
                repoclosure_arch_list = self.repoclosure_map['arches'][arch]

                # Some repos will have additional repos to close against - this
                # helps append
                if len(self.repoclosure_map['repos'][repo]) > 0:
                    for l in self.repoclosure_map['repos'][repo]:
                        stretch = f'--repo={l}'
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
                        '--repo={} --check={} {} -c {} -y '
                        '| tee -a {}/peridot-{}-repoclosure-{}.log').format(
                        repoclosure_arch_list,
                        repo,
                        repo,
                        join_repo_comb,
                        dnf_config,
                        log_root,
                        repo,
                        arch
                )
                with open(repoclosure_entry_point_sh, "w+") as rcep:
                    rcep.write('#!/bin/bash\n')
                    rcep.write('set -o pipefail\n')
                    rcep.write('/usr/bin/dnf install dnf-plugins-core -y\n')
                    rcep.write('/usr/bin/dnf clean all\n')
                    rcep.write(repoclosure_cmd + '\n')
                    rcep.close()
                os.chmod(repoclosure_entry_point_sh, 0o755)
                repo_combination.clear()

            self.log.info('Spawning pods for %s' % repo)
            for pod in repoclosure_entry_name_list:
                podman_cmd_entry = '{} run -d -it -v "{}:{}" -v "{}:{}:z" -v "{}:{}" --name {} --entrypoint {}/{} {}'.format(
                        cmd,
                        self.compose_root,
                        self.compose_root,
                        dnf_config,
                        dnf_config,
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
            pod_watcher = f'{cmd} wait {join_all_pods}'

            watch_man = subprocess.call(
                    shlex.split(pod_watcher),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
            )

            for pod in repoclosure_entry_name_list:
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

            repoclosure_entry_name_list.clear()
            self.log.info('Syncing %s completed' % repo)

        if len(bad_exit_list) > 0:
            self.log.error(
                    Color.BOLD + Color.RED + 'There were issues closing these '
                    'repositories:' + Color.END
            )
            for issue in bad_exit_list:
                self.log.error(issue)


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
            gpg_check: bool = True,
            repo_gpg_check: bool = True,
            extra_dnf_args=None,
            reposync_clean_old: bool = False,
            logger=None,
            log_level='INFO',
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
        self.profile = sigvars['profile']
        self.sigprofile = sigvars['profile']
        self.iso_map = rlvars['iso_map']
        self.distname = config['distname']
        self.fullname = rlvars['fullname']
        self.shortname = config['shortname']
        self.fullversion = rlvars['revision']
        self.sigrepo = repo
        self.checksum = rlvars['checksum']
        self.gpg_check = gpg_check
        self.repo_gpg_check = repo_gpg_check

        # Relevant major version items
        self.sigvars = sigvars
        self.sigrepos = sigvars['repo'].keys()
        self.extra_files = sigvars['extra_files']
        self.gpgkey = rlvars['gpg_key']
        if rlvars['repo_gpg_key']:
            self.gpgkey = rlvars['gpg_key'] + rlvars['repo_gpg_key']
        #self.arches = sigvars['allowed_arches']
        self.project_id = sigvars['project_id']
        if 'additional_dirs' in sigvars:
            self.additional_dirs = sigvars['additional_dirs']

        self.compose_id = '{}-{}-{}'.format(
                self.profile,
                self.major_version,
                config['date_stamp']
        )

        # Templates
        file_loader = FileSystemLoader(f"{_rootdir}/templates")
        self.tmplenv = Environment(loader=file_loader)

        # dnf args
        dnf_args_to_add = []
        if extra_dnf_args:
            if '--delete' in extra_dnf_args:
                raise SystemExit('Please use the --reposync-clean option instead.')

            dnf_args_to_add.extend(extra_dnf_args.split(' '))

        self.extra_dnf_args = dnf_args_to_add.copy()
        self.reposync_clean_old = reposync_clean_old

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
                f"latest-SIG-{self.sigprofile}-{major}"
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
        self.log = logging.getLogger("sigreposync")
        self.log.setLevel(getattr(logging, log_level.upper(), 'INFO'))
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
                '%(asctime)s :: %(name)s :: %(message)s',
                '%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

        self.log.info('sig reposync init')
        self.log.info(self.profile + ' ' + self.major_version)

        # The repo name should be valid
        if self.sigrepo is not None:
            if self.sigrepo not in self.sigrepos:
                self.log.error(
                        Color.FAIL +
                        'Invalid SIG repository: ' +
                        self.profile +
                        ' ' +
                        self.sigrepo
                )

    def run(self):
        """
        This runs the sig sync.
        """
        if self.fullrun and self.sigrepo:
            self.log.error('WARNING: repo ignored when doing a full sync')
        if self.fullrun and self.dryrun:
            self.log.error('A full and dry run is currently not supported.')
            raise SystemExit('\nA full and dry run is currently not supported.')

        # This should create the initial compose dir and set the path.
        # Otherwise, just use the latest link.
        if self.fullrun:
            simplename = 'SIG-' + self.sigprofile
            generated_dir = Shared.generate_compose_dirs(
                    self.compose_base,
                    simplename,
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

        sig_sync_root = os.path.join(
                sync_root,
                self.major_version,
                self.sigprofile
        )

        self.dnf_config = Shared.generate_conf(
                self.profile,
                self.major_version,
                self.sigrepos,
                self.repo_base_url,
                self.project_id,
                self.hashed,
                self.extra_files,
                self.gpgkey,
                self.gpg_check,
                self.repo_gpg_check,
                self.tmplenv,
                self.log
        )

        # dnf config here
        if self.dryrun:
            self.log.error('Dry Runs are not supported just yet. Sorry!')
            raise SystemExit()

        if self.fullrun and self.refresh_extra_files:
            self.log.warning(Color.WARN + 'A full run implies extra files are also deployed.')

        self.sync(self.sigrepo, sync_root, work_root, log_root, global_work_root, self.arch)

        if self.fullrun:
            Shared.deploy_extra_files(self.extra_files, sig_sync_root, global_work_root, self.log)
            Shared.symlink_to_latest(simplename, self.major_version,
                    generated_dir, self.compose_latest_dir, self.log)

        if self.refresh_extra_files and not self.fullrun:
            Shared.deploy_extra_files(self.extra_files, sig_sync_root, global_work_root, self.log)

    def sync(self, repo, sync_root, work_root, log_root, global_work_root, arch=None):
        """
        Calls out syncing of the repos. We generally sync each component of a
        repo:
            * each arch
            * each arch debug
            * each source

        If paralel is true, we will run in podman.
        """
        # I think we need to do a bit of leg work here, there is a chance that
        # a sig may have repos that have repos that are not applicable to all
        # arches...
        if self.parallel:
            self.podman_sync(repo, sync_root, work_root, log_root, global_work_root, arch)
        else:
            Shared.dnf_sync(repo, sync_root, work_root, arch, self.log)

        self.create_additional_dirs(sync_root)

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

        Create sync/root/work/entries
        Generate scripts as needed into dir
        Each container runs their own script
        wait till all is finished
        """
        cmd = Shared.podman_cmd(self.log)
        bad_exit_list = []
        extra_dnf_args = ' '.join(self.extra_dnf_args.copy())
        reposync_delete = '--delete' if self.reposync_clean_old else ''
        self.log.info('Generating container entries')
        entries_dir = os.path.join(work_root, "entries")
        if not os.path.exists(entries_dir):
            os.makedirs(entries_dir, exist_ok=True)

        # yeah, I know.
        if not os.path.exists(global_work_root):
            os.makedirs(global_work_root, exist_ok=True)

        if not os.path.exists(log_root):
            os.makedirs(log_root, exist_ok=True)

        repos_to_sync = self.sigrepos
        if repo and not self.fullrun:
            repos_to_sync = repo.split(',')

        for r in repos_to_sync:
            entry_name_list = []
            repo_name = r
            # Each repo can have specific allowed arches, based on the request
            # of the SIG. What we also want to make sure is that if an arch was
            # asked for but a repo (regardless if we are choosing a repo or not)
            # we have to pass it with a warning.
            arch_sync = self.sigvars['repo'][r]['allowed_arches'].copy()
            if arch:
                arch_sync = arch.split(',')

            for a in arch_sync:
                entry_name = f'{r}-{a}'
                debug_entry_name = f'{r}-debug-{a}'

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
                        self.major_version,
                        self.profile,
                        a,
                        r
                )

                debug_sync_path = os.path.join(
                        sync_root,
                        self.major_version,
                        self.profile,
                        a,
                        r + '-debug'
                )

                gpg_key_list = self.gpgkey
                import_gpg_cmd = f"/usr/bin/rpm --import"
                arch_force_cp = f"/usr/bin/sed 's|$basearch|{a}|g' {self.dnf_config} > {self.dnf_config}.{a}"
                sync_log = f"{log_root}/{repo_name}-{a}.log"
                debug_sync_log = f"{log_root}/{repo_name}-{a}-debug.log"

                metadata_cmd = f"/usr/bin/dnf makecache -c {self.dnf_config}.{a} "\
                        f"--repoid={r} --forcearch {a} --assumeyes 2>&1"

                sync_cmd = f"/usr/bin/dnf reposync -c {self.dnf_config}.{a} --download-metadata "\
                        f"--repoid={r} -p {os_sync_path} --forcearch {a} --norepopath "\
                        f"--remote-time --gpgcheck --assumeyes {reposync_delete} 2>&1"

                debug_metadata_cmd = f"/usr/bin/dnf makecache -c {self.dnf_config}.{a} "\
                        f"--repoid={r}-debug --forcearch {a} --assumeyes 2>&1"

                debug_sync_cmd = f"/usr/bin/dnf reposync -c {self.dnf_config}.{a} "\
                        f"--download-metadata --repoid={r}-debug -p {debug_sync_path} "\
                        f"--forcearch {a} --gpgcheck --norepopath --remote-time "\
                        f"--assumeyes {reposync_delete} 2>&1"

                dnf_plugin_cmd = "/usr/bin/dnf install dnf-plugins-core -y"

                sync_template = self.tmplenv.get_template('reposync.tmpl')
                sync_output = sync_template.render(
                        gpg_key_list=gpg_key_list,
                        import_gpg_cmd=import_gpg_cmd,
                        arch_force_cp=arch_force_cp,
                        dnf_plugin_cmd=dnf_plugin_cmd,
                        sync_cmd=sync_cmd,
                        metadata_cmd=metadata_cmd,
                        sync_log=sync_log,
                        download_path=os_sync_path,
                        deploy_extra_files=True
                )

                debug_sync_template = self.tmplenv.get_template('reposync.tmpl')
                debug_sync_output = debug_sync_template.render(
                        gpg_key_list=gpg_key_list,
                        import_gpg_cmd=import_gpg_cmd,
                        arch_force_cp=arch_force_cp,
                        dnf_plugin_cmd=dnf_plugin_cmd,
                        sync_cmd=debug_sync_cmd,
                        metadata_cmd=debug_metadata_cmd,
                        sync_log=debug_sync_log,
                        download_path=debug_sync_path,
                        deploy_extra_files=True
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
            if (not self.ignore_source and not arch) or (
                    not self.ignore_source and arch == 'source'):
                source_entry_name = f'{r}-source'
                entry_name_list.append(source_entry_name)

                source_entry_point_sh = os.path.join(
                        entries_dir,
                        source_entry_name
                )

                source_sync_path = os.path.join(
                        sync_root,
                        self.major_version,
                        self.profile,
                        'source',
                        r
                )

                source_sync_log = f"{log_root}/{repo_name}-source.log"

                source_metadata_cmd = ("/usr/bin/dnf makecache -c {} --repoid={}-source "
                        "--assumeyes 2>&1").format(
                        self.dnf_config,
                        r
                )

                source_sync_cmd = ("/usr/bin/dnf reposync -c {} "
                        "--download-metadata --repoid={}-source -p {} "
                        "--gpgcheck --norepopath --remote-time --assumeyes {} 2>&1").format(
                        self.dnf_config,
                        r,
                        source_sync_path,
                        reposync_delete
                )

                source_sync_template = self.tmplenv.get_template('reposync-src.tmpl')
                source_sync_output = source_sync_template.render(
                        gpg_key_list=gpg_key_list,
                        import_gpg_cmd=import_gpg_cmd,
                        dnf_plugin_cmd=dnf_plugin_cmd,
                        sync_cmd=source_sync_cmd,
                        metadata_cmd=source_metadata_cmd,
                        sync_log=source_sync_log,
                        download_path=debug_sync_path,
                        deploy_extra_files=True
                )

                source_entry_point_open = open(source_entry_point_sh, "w+")
                source_entry_point_open.write(source_sync_output)
                source_entry_point_open.close()
                os.chmod(source_entry_point_sh, 0o755)

            # Spawn up all podman processes for repo
            self.log.info(Color.INFO + 'Starting podman processes for %s ...' % r)

            #print(entry_name_list)
            for pod in entry_name_list:
                podman_cmd_entry = '{} run -d -it -v "{}:{}" -v "{}:{}:z" -v "{}:{}" --name {} --entrypoint {}/{} {}'.format(
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
            self.log.info(Color.INFO + 'Arches: ' + ' '.join(arch_sync))
            pod_watcher = f'{cmd} wait {join_all_pods}'

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
                sync_root,
                self.distname,
                self.shortname,
                self.fullversion,
                'updates',
                productmd_date
        )

        self.log.info(Color.INFO + 'Metadata files phase completed.')

    def create_additional_dirs(self, sync_root):
        """
        Creates additional directories
        """
        self.log.info(Color.INFO + 'Ensuring additional directories exist')
