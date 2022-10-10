class common:
    def rlver(self, rlver):
        default = "Not Supported"
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

switcher = common()
