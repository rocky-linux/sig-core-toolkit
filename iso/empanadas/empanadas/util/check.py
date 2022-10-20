# Is our arch allowed for this particular release? Some previous releases do
# not support ppc or s390x
from empanadas.common import Color

class Checks:
    """This class helps check some things"""
    def __init__(self, rlvars, arch):
        self.profile = rlvars
        self.arches = rlvars['allowed_arches']
        self.arch = arch

    def check_validity(self):
        """
        Does the arch and profile check for us
        """
        self.check_valid_profile()
        self.check_valid_arch()

    def check_valid_arch(self):
        """
        Validates if the arch we're running on is technically supported.
        """
        if self.arch not in self.arches:
            raise SystemExit(Color.BOLD + 'This architecture is not supported.'
                    + Color.END + '\n\nEnsure that the architecture you are '
                    'building for is supported for this compose process.')

    def check_valid_profile(self):
        """
        Validates if the profile we've selected actually exists
        """
        if len(self.profile['major']) == 0:
            raise SystemExit(Color.BOLD + 'Profile does not exist or major '
                    'version is not defined.' + Color.END + '\n\nEnsure that '
                    'the profile you are loading exists or is configured '
                    'correctly.\n\nNote: A major version MUST exist even for '
                    'SIG syncs.')
