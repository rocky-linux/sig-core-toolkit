HAS_LIBREPO = True
import os
import os.path
import pipes
import shutil

try:
    import librepo
except:
    HAS_LIBREPO = False

class RepoSync:
    """
    This helps us do reposync operations for the base system. SIG syncs are a
    different class entirely. This is on purpose. Please use the SigRepoSync
    class for SIG syncs.
    """
    def __init__(self, rlvars, config, repo=None, nofail: bool = False):
        self.nofail = nofail
        # Relevant config items
        self.major_version = config['rlmacro']
        self.date_stamp = config['date_stamp']
        self.staging_dir = config['staging_root'] + config['category_stub'] + self.major_version
        self.repo_base_url = config['repo_base_url']

        # Relevant major version items
        self.revision = rlvars['revision'] + "-" + rlvars['rclvl']
        self.arches = rlvars['allowed_arches']
        self.project_id = rlvars['project_id']
        self.repo_renames = rlvars['renames']
        self.repos = rlvars['all_repos']
        self.repo = repo

    def run(self):
        pass

    def sync(self):
        cmd = self.reposync_cmd()
        print(self.revision)

    def generate_conf(self, dest_path: str, repo):
        """
        Generates the necessary repo conf file for the operation. This repo
        file should be temporary in nature. This will generate a repo file
        with all repos by default. If a repo is chosen for sync, that will be
        the only one synced.

        :param dest_path: The destination where the temporary conf goes
        :param repo: The repo object to create a file for
        """
        pass

    def reposync_cmd(self) -> str:
        """
        This generates the reposync command. We don't support reposync by
        itself and will raise an error.

        :return: The path to the reposync command. If dnf exists, we'll use
        that.
        """
        cmd = None
        if os.path.exists("/usr/bin/dnf"):
            cmd = "/usr/bin/dnf reposync"
        else:
            raise SystemExit("/usr/bin/dnf was not found. /usr/bin/reposync is "
                    "is not sufficient and you are likely running on an el7 "
                    "system, which tells us that you made changes to these "
                    "tools.")
        return cmd
