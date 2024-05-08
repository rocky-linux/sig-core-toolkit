"""Backend for ImageFactory"""

import json
import os
import pathlib
import tempfile

from .interface import BackendInterface
from empanadas.builders import utils

from attrs import define, field

from typing import List, Optional, Callable, Union

KICKSTART_PATH = pathlib.Path(os.environ.get("KICKSTART_PATH", "/kickstarts"))
STORAGE_DIR = pathlib.Path("/var/lib/imagefactory/storage")


@define(kw_only=True)
class ImageFactoryBackend(BackendInterface):
    """Build an image using ImageFactory"""
    kickstart_arg: List[str] = field(factory=list)
    kickstart_path: pathlib.Path = field(init=False)
    base_uuid: Optional[str] = field(default="")
    target_uuid: Optional[str] = field(default="")
    tdl_path: pathlib.Path = field(init=False)
    out_type: str = field(init=False)
    command_args: List[str] = field(factory=list)
    common_args: List[str] = field(factory=list)
    package_args: List[str] = field(factory=list)
    metadata: pathlib.Path = field(init=False)
    stage_commands: Optional[List[List[Union[str, Callable]]]] = field(init=False)

    # The url to use in the path when fetching artifacts for the build
    kickstart_dir: str = field()  # 'os' or 'kickstart'

    # The git repository to fetch kickstarts from
    kickstart_repo: str = field()

    def prepare(self):
        self.out_type = self.image_format()

        tdl_template = self.ctx.tmplenv.get_template('icicle/tdl.xml.tmpl')

        self.tdl_path = self.render_icicle_template(tdl_template)
        if not self.tdl_path:
            exit(2)

        self.metadata = pathlib.Path(self.ctx.outdir, ".imagefactory-metadata.json")

        self.kickstart_path = pathlib.Path(f"{KICKSTART_PATH}/Rocky-{self.ctx.architecture.major}-{self.ctx.type_variant}.ks")

        self.checkout_kickstarts()
        self.kickstart_arg = self.kickstart_imagefactory_args()

        try:
            os.mkdir(self.ctx.outdir)
        except FileExistsError:
            self.log.info("Directory already exists for this release. If possible, previously executed steps may be skipped")
        except Exception as e:
            self.log.exception("Some other exception occured while creating the output directory", e)
            return 0

        if os.path.exists(self.metadata):
            self.ctx.log.info(f"Found metadata at {self.metadata}")
            with open(self.metadata, "r") as f:
                try:
                    o = json.load(f)
                    self.base_uuid = o['base_uuid']
                    self.target_uuid = o['target_uuid']
                except json.decoder.JSONDecodeError as e:
                    self.ctx.log.exception("Couldn't decode metadata file", e)
                finally:
                    f.flush()

        self.command_args = self._command_args()
        self.package_args = self._package_args()
        self.common_args = self._common_args()

        self.setup_staging()

    def build(self) -> int:
        if self.base_uuid:
            return 0

        self.fix_ks()

        # TODO(neil): this should be a lambda which is called from the function
        ret, out, err, uuid = self.ctx.prepare_and_run(self.build_command(), search=True)
        if uuid:
            self.base_uuid = uuid.rstrip()
            self.save()

        if ret > 0:
            return ret

        ret = self.package()

        if ret > 0:
            return ret


    def clean(self):
        pass

    def save(self):
        with open(self.metadata, "w") as f:
            try:
                o = {
                    name: getattr(self, name) for name in [
                        "base_uuid", "target_uuid"
                    ]
                }
                self.ctx.log.debug(o)
                json.dump(o, f)
            except AttributeError as e:
                self.ctx.log.error("Couldn't find attribute in object. Something is probably wrong", e)
            except Exception as e:
                self.ctx.log.exception(e)
            finally:
                f.flush()

    def package(self) -> int:
        # Some build types don't need to be packaged by imagefactory
        # @TODO remove business logic if possible
        if self.ctx.image_type in ["GenericCloud", "EC2", "Azure", "Vagrant", "OCP", "RPI", "GenericArm"]:
            self.target_uuid = self.base_uuid if hasattr(self, 'base_uuid') else ""

        if self.target_uuid:
            return 0

        ret, out, err, uuid = self.ctx.prepare_and_run(self.package_command(), search=True)
        if uuid:
            self.target_uuid = uuid.rstrip()
            self.save()
        return ret

    def stage(self) -> int:
        """ Stage the artifacst from wherever they are (unpacking and converting if needed)"""
        self.ctx.log.info("Executing staging commands")
        if not hasattr(self, 'stage_commands'):
            return 0

        returns = []
        for command in self.stage_commands:  # type: ignore
            ret, out, err, _ = self.ctx.prepare_and_run(command, search=False)
            returns.append(ret)

        if (res := all(ret > 0 for ret in returns) > 0):
            raise Exception(res)

        return 0

    def checkout_kickstarts(self) -> int:
        cmd = ["git", "clone", "--branch", f"r{self.ctx.architecture.major}",
               self.kickstart_repo, f"{KICKSTART_PATH}"]
        ret, out, err, _ = self.ctx.prepare_and_run(cmd, search=False)
        self.ctx.log.debug(out)
        self.ctx.log.debug(err)
        if ret > 0:
            ret = self.pull_kickstarts()
        return ret

    def pull_kickstarts(self) -> int:
        cmd: utils.CMD_PARAM_T = ["git", "-C", f"{KICKSTART_PATH}", "reset", "--hard", "HEAD"]
        ret, out, err, _ = self.ctx.prepare_and_run(cmd, search=False)
        self.ctx.log.debug(out)
        self.ctx.log.debug(err)
        if ret == 0:
            cmd = ["git", "-C", f"{KICKSTART_PATH}",  "pull"]
            ret, out, err, _ = self.ctx.prepare_and_run(cmd, search=False)
            self.ctx.log.debug(out)
            self.ctx.log.debug(err)
        return ret

    def _command_args(self):
        args_mapping = {
            "debug": "--debug",
        }
        # NOTE(neil): i'm intentionally leaving this as is; deprecated
        return [param for name, param in args_mapping.items() if self.ctx.debug]

    def _package_args(self) -> List[str]:
        if self.ctx.image_type in ["Container"]:
            return ["--parameter", "compress", "xz"]
        return [""]

    def _common_args(self) -> List[str]:
        args = []
        if self.ctx.image_type in ["Container"]:
            args = ["--parameter", "offline_icicle", "true"]
        if self.ctx.image_type in ["GenericCloud", "EC2", "Vagrant", "Azure", "OCP", "RPI", "GenericArm"]:
            args = ["--parameter", "generate_icicle", "false"]
        return args

    def image_format(self) -> str:
        mapping = {
                "Container": "docker"
        }
        return mapping[self.ctx.image_type] if self.ctx.image_type in mapping.keys() else ''

    def kickstart_imagefactory_args(self) -> List[str]:

        if not self.kickstart_path.is_file():
            self.ctx.log.warning(f"Kickstart file is not available: {self.kickstart_path}")
            if not self.ctx.debug:
                self.ctx.log.warning("Exiting because debug mode is not enabled.")
                exit(2)

        return ["--file-parameter", "install_script", str(self.kickstart_path)]

    def render_icicle_template(self, tdl_template) -> pathlib.Path:
        output = tempfile.NamedTemporaryFile(delete=False).name
        return utils.render_template(output, tdl_template,
                                     architecture=self.ctx.architecture.name,
                                     iso8601date=self.ctx.build_time.strftime("%Y%m%d"),
                                     installdir=self.kickstart_dir,
                                     major=self.ctx.architecture.major,
                                     minor=self.ctx.architecture.minor,
                                     release=self.ctx.release,
                                     size="10G",
                                     type=self.ctx.image_type,
                                     utcnow=self.ctx.build_time,
                                     version_variant=self.ctx.architecture.version if not self.ctx.variant else f"{self.ctx.architecture.version}-{self.ctx.variant}",
                                     )

    def build_command(self) -> List[str]:
        build_command = ["imagefactory", "--timeout", self.ctx.timeout,
                         *self.command_args, "base_image", *self.common_args,
                         *self.kickstart_arg, self.tdl_path]
        return build_command

    def package_command(self) -> List[str]:
        package_command = ["imagefactory", *self.command_args, "target_image",
                           self.out_type, *self.common_args,
                           "--id", f"{self.base_uuid}",
                           *self.package_args,
                           "--parameter", "repository", self.ctx.outname]
        return package_command

    def fix_ks(self):
        cmd: utils.CMD_PARAM_T = ["sed", "-i", f"s,$basearch,{self.ctx.architecture.name},", str(self.kickstart_path)]
        self.ctx.prepare_and_run(cmd, search=False)

    def setup_staging(self):
        # Yes, this is gross. I'll fix it later.
        if self.ctx.image_type in ["Container"]:
            self.stage_commands = [
                    ["tar", "-C", f"{self.ctx.outdir}", "--strip-components=1", "-x", "-f", lambda: f"{STORAGE_DIR}/{self.target_uuid}.body", "*/layer.tar"],
                    ["xz",  f"{self.ctx.outdir}/layer.tar"]
            ]
        if self.ctx.image_type in ["RPI"]:
            self.stage_commands = [
                    ["cp", lambda: f"{STORAGE_DIR}/{self.target_uuid}.body", f"{self.ctx.outdir}/{self.ctx.outname}.raw"],
                    ["xz",  f"{self.ctx.outdir}/{self.ctx.outname}.raw"]
            ]
        if self.ctx.image_type in ["GenericCloud", "OCP", "GenericArm"]:
            self.stage_commands = [
                    ["qemu-img", "convert", "-c", "-f", "raw", "-O", "qcow2",
                     lambda: f"{STORAGE_DIR}/{self.target_uuid}.body", f"{self.ctx.outdir}/{self.ctx.outname}.qcow2"]
            ]
        if self.ctx.image_type in ["EC2"]:
            self.stage_commands = [
                    ["qemu-img", "convert", "-f", "raw", "-O", "qcow2", lambda: f"{STORAGE_DIR}/{self.target_uuid}.body", f"{self.ctx.outdir}/{self.ctx.outname}.qcow2"]
            ]
        if self.ctx.image_type in ["Azure"]:
            self.stage_commands = [
                    ["/prep-azure.sh", lambda: f"{STORAGE_DIR}/{self.target_uuid}.body", f"{STORAGE_DIR}"],
                    ["cp", lambda: f"{STORAGE_DIR}/{self.target_uuid}.vhd", f"{self.ctx.outdir}/{self.ctx.outname}.vhd"]
            ]
        if self.ctx.image_type in ["Vagrant"]:
            _map = {
                    "Vbox": {"format": "vmdk", "provider": "virtualbox"},
                    "Libvirt": {"format": "qcow2", "provider": "libvirt", "virtual_size": 10},
                    "VMware": {"format": "vmdk", "provider": "vmware_desktop"}
                    }
            output = f"{_map[self.ctx.variant]['format']}"  # type: ignore
            provider = f"{_map[self.ctx.variant]['provider']}"  # type: ignore

            # pop from the options map that will be passed to the vagrant metadata.json
            convert_options = _map[self.ctx.variant].pop('convertOptions') if 'convertOptions' in _map[self.ctx.variant].keys() else ''  # type: ignore

            self.stage_commands = [
                    ["qemu-img", "convert", "-c", "-f", "raw", "-O", output, *convert_options,
                     lambda: f"{STORAGE_DIR}/{self.target_uuid}.body", f"{self.ctx.outdir}/{self.ctx.outname}.{output}"],
                    ["tar", "-C", self.ctx.outdir, "-czf", f"/tmp/{self.ctx.outname}.box", '.'],
                    ["mv", f"/tmp/{self.ctx.outname}.box", self.ctx.outdir]
            ]
            self.prepare_vagrant(_map[self.ctx.variant])

        if self.stage_commands:
            self.stage_commands.append(["cp", "-v", lambda: f"{STORAGE_DIR}/{self.target_uuid}.meta", f"{self.ctx.outdir}/build.meta"])

    def prepare_vagrant(self, options):
        """Setup the output directory for the Vagrant type variant, dropping templates as required"""

        templates = {}
        templates['Vagrantfile'] = self.ctx.tmplenv.get_template(f"vagrant/Vagrantfile.{self.ctx.variant}")
        templates['metadata.json'] = self.ctx.tmplenv.get_template('vagrant/metadata.tmpl.json')
        templates['info.json'] = self.ctx.tmplenv.get_template('vagrant/info.tmpl.json')

        if self.ctx.variant == "VMware":
            templates[f"{self.ctx.outname}.vmx"] = self.ctx.tmplenv.get_template('vagrant/vmx.tmpl')

        if self.ctx.variant == "Vbox":
            templates['box.ovf'] = self.ctx.tmplenv.get_template('vagrant/box.tmpl.ovf')

        if self.ctx.variant == "Libvirt":
            # Libvirt vagrant driver expects the qcow2 file to be called box.img.
            qemu_command_index = [i for i, d in enumerate(self.stage_commands) if d[0] == "qemu-img"][0]
            self.stage_commands.insert(qemu_command_index+1, ["mv", f"{self.ctx.outdir}/{self.ctx.outname}.qcow2", f"{self.ctx.outdir}/box.img"])

        for name, template in templates.items():
            utils.render_template(f"{self.ctx.outdir}/{name}", template,
                                  name=self.ctx.outname,
                                  arch=self.ctx.architecture.name,
                                  options=options
                                  )
