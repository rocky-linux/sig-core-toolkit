import sys

class common:
    def rlver(self, rlver, stream=False, all_repo=False):
        default = "Not Supported"
        if (stream and all_repo):
            print("incompatible options used")
            sys.exit(1)

        if stream:
            return getattr(self, 'c' + str(rlver) + 's', lambda: default)()

        if all_repo:
            return getattr(self, 'rl' + str(rlver) + 'all', lambda: default)()

        return getattr(self, 'rl' + str(rlver), lambda: default)()

    def rl8(self):
        REPOS = {
                'AppStream': ['aarch64', 'x86_64'],
                'BaseOS': ['aarch64', 'x86_64'],
                'HighAvailability': ['aarch64', 'x86_64'],
                'PowerTools': ['aarch64', 'x86_64'],
                'ResilientStorage': ['aarch64', 'x86_64'],
                'RT': ['x86_64'],
        }
        return REPOS

    def rl9(self):
        REPOS = {
                'AppStream': ['aarch64', 'ppc64le', 's390x', 'x86_64'],
                'BaseOS': ['aarch64', 'ppc64le', 's390x', 'x86_64'],
                'CRB': ['aarch64', 'ppc64le', 's390x', 'x86_64'],
                'HighAvailability': ['aarch64', 'ppc64le', 's390x', 'x86_64'],
                'NFV': ['x86_64'],
                'ResilientStorage': ['ppc64le', 's390x', 'x86_64'],
                'RT': ['x86_64'],
                'SAP': ['ppc64le', 's390x', 'x86_64'],
                'SAPHANA': ['ppc64le', 'x86_64']
        }
        return REPOS

    def rl10(self):
        REPOS = {
                'AppStream': ['aarch64', 'ppc64le', 's390x', 'x86_64'],
                'BaseOS': ['aarch64', 'ppc64le', 's390x', 'x86_64'],
                'CRB': ['aarch64', 'ppc64le', 's390x', 'x86_64'],
                'HighAvailability': ['aarch64', 'ppc64le', 's390x', 'x86_64'],
                'NFV': ['x86_64'],
                'RT': ['x86_64'],
                'SAP': ['ppc64le', 's390x', 'x86_64'],
                'SAPHANA': ['ppc64le', 'x86_64']
        }
        return REPOS

    def rl8all(self):
        REPOS = {
                'dist-rocky8-lookahead-build': ['aarch64', 'x86_64', 'i386'],
        }
        return REPOS

    def rl9all(self):
        REPOS = {
                'all': ['aarch64', 'ppc64le', 's390x', 'x86_64'],
        }
        return REPOS

    def rl10all(self):
        REPOS = {
                'all': ['aarch64', 'ppc64le', 's390x', 'x86_64'],
        }
        return REPOS

    # Parse tags of koji
    def c8s(self):
        REPOS = {
                'c8s-build': ['aarch64', 'ppc64le', 'x86_64'],
        }
        return REPOS

    def c9s(self):
        REPOS = {
                'c9s-build': ['aarch64', 'ppc64le', 's390x', 'x86_64'],
        }
        return REPOS

    def c10s(self):
        REPOS = {
                'c10s-build': ['aarch64', 'ppc64le', 's390x', 'x86_64'],
        }
        return REPOS

    def r8lh(self):
        REPOS = {
                'dist-rocky8-lookahead-build': ['aarch64', 'i386', 'x86_64'],
        }
        return REPOS

switcher = common()
