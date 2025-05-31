"""Backend for Kiwi"""

from .interface import BackendInterface
from .kiwi_imagedata import ImagesData

from empanadas.builders import utils
from empanadas.common import AttributeDict

from attrs import define, field
from functools import wraps
from typing import List

import git
import os
import pathlib
import tempfile
import shutil
import sys

# TODO(neil): this should be part of the config, somewhere
temp = AttributeDict(
    {
        "Azure": {
            "kiwiType": "oem",
            "kiwiProfile": "Cloud-Azure",
            "fileType": "raw",  # post-converted into vhd on MB boundary
            "outputKey": "disk_format_image",
        },
        "OCP": {
            "kiwiType": "oem",
            "kiwiProfile": "Cloud-OCP",
            "fileType": "qcow2",
            "outputKey": "disk_format_image",
        },
        "GenericCloud": {
            "kiwiType": "oem",
            "kiwiProfile": "Cloud-GenericCloud",
            "fileType": "qcow2",
            "outputKey": "disk_format_image",
        },
        "EC2": {
            "kiwiType": "oem",
            "kiwiProfile": "Cloud-EC2",
            "fileType": "qcow2",
            "outputKey": "disk_format_image",
        },
        "Vagrant": {
            "kiwiType": "oem",
            "kiwiProfile": "Vagrant",
            "fileType": "box",
            "outputKey": "disk_format_image",
        },
        "Container": {
            "kiwiType": "oci",
            "kiwiProfile": "Container",
            "fileType": "tar.xz",
            "outputKey": "container"
        },
        "SBC": {
            "kiwiType": "oem",
            "kiwiProfile": "SBC",
            "fileType": "raw",
            "outputKey": "disk_image"
        },
        "WSL": {
            "kiwiType": "wsl",
            "kiwiProfile": "WSL",
            "fileType": "wsl",
            "outputKey": "container"
        }
    }
)


def ensure_kiwi_conf(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, 'kiwi_conf') or self.kiwi_conf is None:
            self.kiwi_conf = temp[self.ctx.image_type]
        return func(self, *args, **kwargs)
    return wrapper


@define
class KiwiBackend(BackendInterface):
    """Build an image using Kiwi"""

    kiwi_file: str
    build_args: List[str] = field(factory=list)
    image_result: ImagesData = field(init=False)
    kiwi_conf: AttributeDict = field(init=False)

    def prepare(self):
        """
        Checkout mock-rocky-configs and rocky-kiwi-descriptions,
        init the mock env, and setup to run kiwi
        """
        self.checkout_repos()
        self.setup_mock()
        self.setup_kiwi()

    @ensure_kiwi_conf
    def build(self):
        self.build_args += [f"--type={self.kiwi_conf.kiwiType}", f"--profile={self.kiwi_conf.kiwiProfile}-{self.ctx.variant}"]

        kiwi_command = [
            "kiwi-ng", "--color-output",
            "--kiwi-file", self.kiwi_file,
            *self.build_args,
        ]
        if self.ctx.debug:
            kiwi_command.append("--debug")

        kiwi_system_command = [
            "system", "build",
            "--description='/builddir/rocky-kiwi-descriptions'",
            "--target-dir", f"/builddir/{self.ctx.outdir}"
        ]

        build_command = [
            "--shell", "--enable-network", "--", *kiwi_command, *kiwi_system_command
        ]
        ret, out, err = self.run_mock_command(build_command)
        if ret > 0:
            raise Exception(f"Kiwi build failed: code {ret}")
            sys.exit(ret)

    @ensure_kiwi_conf
    def stage(self):
        ret, out, err = self.run_mock_command(["--copyout", f"/builddir/{self.ctx.outdir}", self.ctx.outdir])
        if ret > 0:
            raise Exception("failed to copy build result out")

        kiwi_result_path = pathlib.Path(f"{self.ctx.outdir}/kiwi.result.json")
        if not os.path.exists(kiwi_result_path):
            raise Exception("Missing kiwi.result.json. Aborting")

        with open(kiwi_result_path, "r") as kiwi_result:
            self.image_result = ImagesData.from_json(kiwi_result.read()).images

        source = self.image_result[self.kiwi_conf.outputKey].filename
        filetype = self.kiwi_conf.fileType

        source = utils.remove_first_directory(source)
        dest = f"{self.ctx.outdir}/{self.ctx.outname}.{filetype}"

        # NOTE(neil): only because we are preparing the 'final' image in clean step...
        if self.ctx.image_type == 'Container':
            dest = f"{self.ctx.outdir}/{self.ctx.outname}.oci"

        try:
            shutil.move(source, dest)
        except Exception as e:
            raise e

        # TODO(neil): refactor
        if self.ctx.image_type == 'Azure':
            try:
                utils.resize_and_convert_raw_image_to_vhd(dest, self.ctx.outdir)
                # Remove old raw image
                pathlib.Path(f"{self.ctx.outdir}/{self.ctx.outname}.raw").unlink()
            except Exception as e:
                raise e

    def clean(self):
        # TODO(neil): refactor
        if self.ctx.image_type == 'Container':
            # need to do this before we remove it, otherwise we have to extract from the OCI tarball
            root = f"/builddir{self.ctx.outdir}"
            builddir = f"{root}/build/image-root"
            ret, out, err = self.run_mock_command(["--shell", "--", "tar", "-C", builddir, "-cJf", f"{root}/{self.ctx.outname}.tar.xz", "."])
            if ret > 0:
                raise Exception(err)

        ret, out, err = self.run_mock_command(["--shell", "rm", "-fr", f"/builddir/{self.ctx.outdir}/build/"])
        return ret

    def run_mock_command(self, mock_command: List[str]):
        mock_args = ["--configdir", "/tmp/mock-rocky-configs/etc/mock", "-r", f"rl-9-{self.ctx.architecture.name}-core-infra"]
        if self.ctx.image_type not in ['Container']:
            mock_args.append("--isolation=simple")
        command = [
            "mock",
            *mock_args,
            *mock_command,
        ]
        ret, out, err, _ = self.ctx.prepare_and_run(command)
        return ret, out, err

    def setup_mock(self):
        # TODO(neil): add error checking
        ret, out, err = self.run_mock_command(["--init"])

        packages = [
            "kiwi-boxed-plugin",
            "kiwi-cli",
            "git",
            "dracut-kiwi-live",
            "fuse-overlayfs",
            "kiwi-systemdeps-bootloaders",
            "kiwi-systemdeps-containers",
            "kiwi-systemdeps-core",
            "kiwi-systemdeps-disk-images",
            "kiwi-systemdeps-filesystems",
            "kiwi-systemdeps-image-validation",
            "kiwi-systemdeps-iso-media",
            "epel-release",
            "rocky-release-core"
        ]
        ret, out, err = self.run_mock_command(["--install", *packages])

        ret, out, err = self.run_mock_command(["--copyin", "/tmp/rocky-kiwi-descriptions", "/builddir/"])
        return ret

    def checkout_repos(self):
        """
        Checkout sig_core/mock-rocky-configs and sig_core/rocky-kiwi-descriptions to /tmp
        """
        repos = {
            "mock-rocky-configs": "main",
            "rocky-kiwi-descriptions": "r9"
        }

        for repo, branch in repos.items():
            repo_url = f"https://git.resf.org/sig_core/{repo}"
            clone_dir = f"/tmp/{repo}"

            if os.path.isdir(os.path.join(clone_dir, ".git")):
                try:
                    # The directory exists and is a git repository, so attempt to pull the latest changes
                    git.Repo(clone_dir).remotes.origin.pull(branch)
                    self.ctx.log.info(f"pulled the latest changes for {branch} branch in {clone_dir}")
                except Exception as e:
                    raise Exception(f"Failed to pull the repository: {str(e)}")
                finally:
                    continue

            try:
                git.Repo.clone_from(repo_url, clone_dir, branch=branch)
                print(f"Repository cloned into {clone_dir}")
            except Exception as e:
                print(f"Failed to clone repository: {str(e)}")

    def setup_kiwi(self):
        self.ctx.log.info("Generating kiwi.yml from template")
        template = self.ctx.tmplenv.get_template('kiwi/kiwi.yml.j2')
        output = tempfile.NamedTemporaryFile(delete=False).name
        res = utils.render_template(output, template)

        self.ctx.log.info("Copying generated kiwi.yml into build root")
        ret, out, err = self.run_mock_command(["--copyin", res, "/etc/kiwi.yml"])
        if ret > 0:
            raise Exception("Failed to configure kiwi")

        self.ctx.log.info("Finished setting up kiwi")
