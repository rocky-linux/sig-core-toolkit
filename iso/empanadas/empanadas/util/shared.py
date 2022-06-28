# These are shared utilities used

import os
import hashlib
import productmd.treeinfo

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
        variant.repository = "."
        variant.packages = "Packages"
        ti.variants.add(variant)
        ti.dump(file_path)

    @staticmethod
    def treeinfo_modify_write():
        """
        Modifies a specific treeinfo with already available data. This is in
        the case of modifying treeinfo for primary repos or images.
        """


    @staticmethod
    def discinfo_write(timestamp, fullname, arch, file_path):
        """
        Ensure discinfo is written correctly
        """
        data = [
            "%s" % timestamp,
            "%s" % fullname,
            "%s" % arch,
            "ALL"
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
