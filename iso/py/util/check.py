# Is our arch allowed for this particular release? Some previous releases do
# not support ppc or s390x
from common import Color
class Checks:
    """This class helps check some things"""
    def __init__(self, rlvars, arch):
        self.arches = rlvars['allowed_arches']
        self.arch = arch

    def check_valid_arch(self):
        if self.arch not in self.arches:
            raise SystemExit(Color.BOLD + 'This architecture is not supported.'
                    + Color.END + '\n\nEnsure that the architecture you are '
                    'building for is supported for this compose process.')
