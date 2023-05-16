# Builds an image given a version, type, variant, and architecture
# Defaults to the running host's architecture

import argparse
import datetime
import json
import logging
import os
import pathlib
import platform
import subprocess
import sys
import tempfile
import time

from attrs import define, Factory, field, asdict
from botocore import args
from jinja2 import Environment, FileSystemLoader, Template
from typing import Callable, List, NoReturn, Optional, Tuple, IO, Union

from empanadas.common import Architecture, rldict, valid_type_variant
from empanadas.common import _rootdir

parser = argparse.ArgumentParser(description="ISO Compose")

parser.add_argument('--version', type=str, help="Release Version (8.6, 9.1)", required=True)
parser.add_argument('--rc', action='store_true', help="Release Candidate")
parser.add_argument('--kickstartdir', action='store_true', help="Use the kickstart dir instead of the os dir for repositories")
parser.add_argument('--debug', action='store_true', help="debug?")
parser.add_argument('--type', type=str, help="Image type (container, genclo, azure, aws, vagrant)", required=True)
parser.add_argument('--variant', type=str, help="", required=False)
parser.add_argument('--release', type=str, help="Image release for subsequent builds with the same date stamp (rarely needed)", required=False)
parser.add_argument('--kube', action='store_true', help="output as a K8s job(s)", required=False)
parser.add_argument('--timeout', type=str, help="change timeout for imagefactory build process (default 3600)", required=False, default='3600')


results = parser.parse_args()
rlvars = rldict[results.version]
major = rlvars["major"]


debug = results.debug

log = logging.getLogger(__name__)
log.setLevel(logging.INFO if not debug else logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO if not debug else logging.DEBUG)
formatter = logging.Formatter(
        '%(asctime)s :: %(name)s :: %(message)s',
        '%Y-%m-%d %H:%M:%S'
)
handler.setFormatter(formatter)
log.addHandler(handler)

STORAGE_DIR = pathlib.Path("/var/lib/imagefactory/storage")
KICKSTART_PATH = pathlib.Path(os.environ.get("KICKSTART_PATH", "/kickstarts"))
BUILDTIME = datetime.datetime.utcnow()


CMD_PARAM_T = List[Union[str, Callable[..., str]]]

@define(kw_only=True)
class ImageBuild:
    architecture: Architecture = field()
    base_uuid: Optional[str] = field(default="")
    cli_args: argparse.Namespace = field()
    command_args: List[str] = field(factory=list)
    common_args: List[str] = field(factory=list)
    debug: bool = field(default=False)
    image_type: str = field()
    job_template: Optional[Template] = field(init=False)
    kickstart_arg: List[str] = field(factory=list)
    kickstart_path: pathlib.Path = field(init=False)
    metadata: pathlib.Path = field(init=False)
    out_type: str = field(init=False)
    outdir: pathlib.Path = field(init=False) 
    outname: str = field(init=False)
    package_args: List[str] = field(factory=list)
    release: int = field(default=0)
    stage_commands: Optional[List[List[Union[str,Callable]]]] = field(init=False)
    target_uuid: Optional[str] = field(default="")
    tdl_path: pathlib.Path = field(init=False)
    template: Template = field()
    timeout: str = field(default='3600')
    type_variant: str = field(init=False) 
    variant: Optional[str] = field()

    def __attrs_post_init__(self):
        self.tdl_path = self.render_icicle_template()
        if not self.tdl_path:
            exit(2)
        self.type_variant = self.type_variant_name()
        self.outdir, self.outname = self.output_name()
        self.out_type = self.image_format()
        self.command_args = self._command_args()
        self.package_args = self._package_args()
        self.common_args = self._common_args()

        self.metadata = pathlib.Path(self.outdir, ".imagefactory-metadata.json")

        self.kickstart_path = pathlib.Path(f"{KICKSTART_PATH}/Rocky-{self.architecture.major}-{self.type_variant}.ks")

        self.checkout_kickstarts()
        self.kickstart_arg = self.kickstart_imagefactory_args()

        try:
            os.mkdir(self.outdir)
        except FileExistsError as e:
            log.info("Directory already exists for this release. If possible, previously executed steps may be skipped")
        except Exception as e:
            log.exception("Some other exception occured while creating the output directory", e)
            return 0

        if os.path.exists(self.metadata):
            with open(self.metadata, "r") as f:
                try:
                    o = json.load(f)
                    self.base_uuid = o['base_uuid']
                    self.target_uuid = o['target_uuid']
                except json.decoder.JSONDecodeError as e:
                    log.exception("Couldn't decode metadata file", e)
                finally:
                    f.flush()

        # Yes, this is gross. I'll fix it later.
        if self.image_type in ["Container"]:
            self.stage_commands = [
                    ["tar", "-C", f"{self.outdir}", "--strip-components=1", "-x", "-f", lambda: f"{STORAGE_DIR}/{self.target_uuid}.body", "*/layer.tar"],
                    ["xz",  f"{self.outdir}/layer.tar"]
            ]
        if self.image_type in ["RPI"]:
            self.stage_commands = [
                    ["cp", lambda: f"{STORAGE_DIR}/{self.target_uuid}.body", f"{self.outdir}/{self.outname}.raw"],
                    ["xz",  f"{self.outdir}/{self.outname}.raw"]
            ]
        if self.image_type in ["GenericCloud", "OCP", "GenericArm"]:
            self.stage_commands = [
                    ["qemu-img", "convert", "-c", "-f", "raw", "-O", "qcow2", lambda: f"{STORAGE_DIR}/{self.target_uuid}.body", f"{self.outdir}/{self.outname}.qcow2"]
            ]
        if self.image_type in ["EC2"]:
            self.stage_commands = [
                    ["qemu-img", "convert", "-f", "raw", "-O", "qcow2", lambda: f"{STORAGE_DIR}/{self.target_uuid}.body", f"{self.outdir}/{self.outname}.qcow2"]
            ]
        if self.image_type in ["Azure"]:
            self.stage_commands = [
                    ["/prep-azure.sh", lambda: f"{STORAGE_DIR}/{self.target_uuid}.body", f"{STORAGE_DIR}"],
                    ["cp", lambda: f"{STORAGE_DIR}/{self.target_uuid}.vhd", f"{self.outdir}/{self.outname}.vhd"]
            ]
        if self.image_type in ["Vagrant"]:
            _map = {
                    "Vbox": {"format": "vmdk", "provider": "virtualbox"},
                    "Libvirt": {"format": "qcow2", "provider": "libvirt", "virtual_size": 10},
                    "VMware": {"format": "vmdk", "provider": "vmware_desktop"}
                    }
            output = f"{_map[self.variant]['format']}" #type: ignore
            provider = f"{_map[self.variant]['provider']}" # type: ignore

            # pop from the options map that will be passed to the vagrant metadata.json
            convert_options = _map[self.variant].pop('convertOptions') if 'convertOptions' in _map[self.variant].keys() else '' #type: ignore


            self.stage_commands = [
                    ["qemu-img", "convert", "-c", "-f", "raw", "-O", output, *convert_options, lambda: f"{STORAGE_DIR}/{self.target_uuid}.body", f"{self.outdir}/{self.outname}.{output}"],
                    ["tar", "-C", self.outdir, "-czf", f"/tmp/{self.outname}.box", '.'],
                    ["mv", f"/tmp/{self.outname}.box", self.outdir]
            ]
            self.prepare_vagrant(_map[self.variant])

        if self.stage_commands:
            self.stage_commands.append(["cp", "-v",  lambda: f"{STORAGE_DIR}/{self.target_uuid}.meta", f"{self.outdir}/build.meta"])


    def prepare_vagrant(self, options):
        """Setup the output directory for the Vagrant type variant, dropping templates as required"""
        file_loader = FileSystemLoader(f"{_rootdir}/templates")
        tmplenv = Environment(loader=file_loader)

        templates = {}
        templates['Vagrantfile'] = tmplenv.get_template(f"vagrant/Vagrantfile.{self.variant}")
        templates['metadata.json'] = tmplenv.get_template('vagrant/metadata.tmpl.json')
        templates['info.json'] = tmplenv.get_template('vagrant/info.tmpl.json')

        if self.variant == "VMware":
            templates[f"{self.outname}.vmx"] = tmplenv.get_template('vagrant/vmx.tmpl')

        if self.variant == "Vbox":
            templates['box.ovf'] = tmplenv.get_template('vagrant/box.tmpl.ovf')

        if self.variant == "Libvirt":
            # Libvirt vagrant driver expects the qcow2 file to be called box.img.
            qemu_command_index = [i for i, d in enumerate(self.stage_commands) if d[0] == "qemu-img"][0]
            self.stage_commands.insert(qemu_command_index+1, ["mv", f"{self.outdir}/{self.outname}.qcow2", f"{self.outdir}/box.img"])

        for name, template in templates.items():
            self.render_template(f"{self.outdir}/{name}", template,
                    name=self.outname,
                    arch=self.architecture.name,
                    options=options
            )

    def checkout_kickstarts(self) -> int:
        cmd = ["git", "clone", "--branch", f"r{self.architecture.major}", rlvars['livemap']['git_repo'], f"{KICKSTART_PATH}"]
        ret, out, err, _ = self.runCmd(cmd, search=False)
        log.debug(out)
        log.debug(err)
        if ret > 0:
            ret = self.pull_kickstarts()
        return ret

    def pull_kickstarts(self) -> int:
        cmd: CMD_PARAM_T = ["git", "-C", f"{KICKSTART_PATH}", "reset", "--hard", "HEAD"]
        ret, out, err, _ = self.runCmd(cmd, search=False)
        log.debug(out)
        log.debug(err)
        if ret == 0:
            cmd = ["git", "-C", f"{KICKSTART_PATH}",  "pull"]
            ret, out, err, _ = self.runCmd(cmd, search=False)
            log.debug(out)
            log.debug(err)
        return ret


    def output_name(self) -> Tuple[pathlib.Path, str]:
        directory = f"Rocky-{self.architecture.major}-{self.type_variant}-{self.architecture.version}-{BUILDTIME.strftime('%Y%m%d')}.{self.release}"
        name = f"{directory}.{self.architecture.name}"
        outdir = pathlib.Path(f"/tmp/", directory)
        return outdir, name
    
    def type_variant_name(self):
        return self.image_type if not self.variant else f"{self.image_type}-{self.variant}"

    def _command_args(self):
        args_mapping = {
            "debug": "--debug",
        }
        return [param for name, param in args_mapping.items() if getattr(self.cli_args, name)]

    def _package_args(self) -> List[str]:
        if self.image_type in ["Container"]:
            return ["--parameter", "compress", "xz"]
        return [""]

    def _common_args(self) -> List[str]:
        args = []
        if self.image_type in ["Container"]:
            args = ["--parameter", "offline_icicle", "true"]
        if self.image_type in ["GenericCloud", "EC2", "Vagrant", "Azure", "OCP", "RPI", "GenericArm"]:
            args = ["--parameter", "generate_icicle", "false"]
        return args

    def image_format(self) -> str:
        mapping = {
                "Container": "docker"
        }
        return mapping[self.image_type] if self.image_type in mapping.keys() else ''

    def kickstart_imagefactory_args(self) -> List[str]:

        if not self.kickstart_path.is_file():
            log.warn(f"Kickstart file is not available: {self.kickstart_path}")
            if not debug:
                log.warn("Exiting because debug mode is not enabled.")
                exit(2)

        return ["--file-parameter", "install_script", str(self.kickstart_path)]

    def render_template(self, path, template, **kwargs) -> pathlib.Path:
        with open(path, "wb") as f:
            _template = template.render(**kwargs)
            f.write(_template.encode())
            f.flush()
        output = pathlib.Path(path)
        if not output.exists():
            log.error("Failed to write template")
            raise Exception("Failed to template")
        return output

    def render_icicle_template(self) -> pathlib.Path:
        output = tempfile.NamedTemporaryFile(delete=False).name
        return self.render_template(output, self.template,
                architecture=self.architecture.name,
                iso8601date=BUILDTIME.strftime("%Y%m%d"),
                installdir="kickstart" if self.cli_args.kickstartdir else "os",
                major=self.architecture.major,
                minor=self.architecture.minor,
                release=self.release,
                size="10G",
                type=self.image_type,
                utcnow=BUILDTIME,
                version_variant=self.architecture.version if not self.variant else f"{self.architecture.version}-{self.variant}",
            )

    def build_command(self) -> List[str]:
        build_command = ["imagefactory", "--timeout", self.timeout, *self.command_args, "base_image", *self.common_args, *self.kickstart_arg, self.tdl_path]
        return build_command
    def package_command(self) -> List[str]:
        package_command = ["imagefactory", *self.command_args, "target_image", self.out_type, *self.common_args,
                            "--id", f"{self.base_uuid}",
                            *self.package_args, 
                            "--parameter", "repository", self.outname,
                ]
        return package_command

    def copy_command(self) -> List[str]:

        copy_command = ["aws", "s3", "cp", "--recursive", f"{self.outdir}/", 
                f"s3://resf-empanadas/buildimage-{self.architecture.version}-{self.architecture.name}/{ self.outname }/{ BUILDTIME.strftime('%s') }/"
                ]

        return copy_command

    def build(self) -> int:
        if self.base_uuid:
            return 0

        self.fix_ks()

        ret, out, err, uuid = self.runCmd(self.build_command()) 
        if uuid:
            self.base_uuid = uuid.rstrip()
            self.save()
        return ret

    def package(self) -> int: 
        # Some build types don't need to be packaged by imagefactory
        # @TODO remove business logic if possible
        if self.image_type in ["GenericCloud", "EC2", "Azure", "Vagrant", "OCP", "RPI"]:
            self.target_uuid = self.base_uuid if hasattr(self, 'base_uuid') else ""

        if self.target_uuid:
            return 0

        ret, out, err, uuid = self.runCmd(self.package_command())
        if uuid:
            self.target_uuid = uuid.rstrip()
            self.save()
        return ret

    def stage(self) -> int:
        """ Stage the artifacst from wherever they are (unpacking and converting if needed)"""
        if not hasattr(self,'stage_commands'):
            return 0

        returns = []
        for command in self.stage_commands: #type: ignore
            ret, out, err, _ = self.runCmd(command, search=False)
            returns.append(ret)

        return all(ret > 0 for ret in returns)

    def copy(self, skip=False) -> int:
        # move or unpack if necessary
        log.info("Executing staging commands")
        if (stage := self.stage() > 0):
            raise Exception(stage)

        if not skip:
            log.info("Copying files to output directory")
            ret, out, err, _ = self.runCmd(self.copy_command(), search=False) 
            return ret

        log.info(f"Build complete! Output available in {self.outdir}/")
        return 0

    def runCmd(self, command: CMD_PARAM_T, search: bool = True) -> Tuple[int, Union[bytes,None], Union[bytes,None], Union[str,None]]:
        prepared, _ = self.prepare_command(command)
        log.info(f"Running command: {' '.join(prepared)}")

        kwargs = {
            "stderr": subprocess.PIPE,
            "stdout": subprocess.PIPE
        }
        if debug: del kwargs["stderr"]

        with subprocess.Popen(prepared,  **kwargs) as p:
            uuid = None
            # @TODO implement this as a callback?
            if search:
                for _, line in enumerate(p.stdout): # type: ignore
                    ln = line.decode()
                    if ln.startswith("UUID: "):
                        uuid = ln.split(" ")[-1]
                        log.debug(f"found uuid: {uuid}")
                
            out, err = p.communicate()
            res = p.wait(), out, err, uuid

            if res[0] > 0:
                log.error(f"Problem while executing command: '{prepared}'")
            if search and not res[3]:
                log.error("UUID not found in stdout. Dumping stdout and stderr")
            self.log_subprocess(res)

            return res

    def prepare_command(self, command_list: CMD_PARAM_T) -> Tuple[List[str],List[None]]:
        """
        Commands may be a callable, which should be a lambda to be evaluated at
        preparation time with available locals. This can be used to, among
        other things, perform lazy evaluations of f-strings which have values
        not available at assignment time. e.g., filling in a second command
        with a value extracted from the previous step or command.

        """

        r = []
        return r, [r.append(c()) if (callable(c) and c.__name__ == '<lambda>') else r.append(str(c)) for c in command_list]

    def log_subprocess(self, result: Tuple[int, Union[bytes, None], Union[bytes, None], Union[str, None]]):
        def log_lines(title, lines):
            log.info(f"====={title}=====")
            log.info(lines.decode())
        log.info(f"Command return code: {result[0]}")
        stdout = result[1]
        stderr = result[2]
        if stdout:
            log_lines("Command STDOUT", stdout)
        if stderr:
            log_lines("Command STDERR", stderr)

    def fix_ks(self):
        cmd: CMD_PARAM_T = ["sed", "-i", f"s,$basearch,{self.architecture.name},", str(self.kickstart_path)]
        self.runCmd(cmd, search=False)

    def render_kubernetes_job(self):
        commands = [self.build_command(), self.package_command(), self.copy_command()]
        if not self.job_template:
            return None
        template = self.job_template.render(
                architecture=self.architecture.name,
                backoffLimit=4,
                buildTime=BUILDTIME.strftime("%s"),
                command=commands,
                imageName="ghcr.io/rockylinux/sig-core-toolkit:latest",
                jobname="buildimage",
                namespace="empanadas",
                major=major,
                restartPolicy="Never",
            )
        return template

    def save(self):
        with open(self.metadata, "w") as f:
            try: 
                o = { name: getattr(self, name) for name in ["base_uuid", "target_uuid"] }
                log.debug(o)
                json.dump(o, f)
            except AttributeError as e:
                log.error("Couldn't find attribute in object. Something is probably wrong", e)
            except Exception as e:
                log.exception(e)
            finally:
                f.flush()

def run():
    try:
        valid_type_variant(results.type, results.variant)
    except Exception as e:
        log.exception(e)
        exit(2)

    file_loader = FileSystemLoader(f"{_rootdir}/templates")
    tmplenv = Environment(loader=file_loader)
    tdl_template = tmplenv.get_template('icicle/tdl.xml.tmpl')

    arches = rlvars['allowed_arches'] if results.kube else [platform.uname().machine]

    for architecture in arches:
        IB = ImageBuild(
                architecture=Architecture.from_version(architecture, rlvars['revision']),
                cli_args=results,
                debug=results.debug,
                image_type=results.type, 
                release=results.release if results.release else 0,
                template=tdl_template,
                variant=results.variant,
        )
        if results.kube:
            IB.job_template = tmplenv.get_template('kube/Job.tmpl')
            #commands = IB.kube_commands()
            print(IB.render_kubernetes_job())
        else:
            ret = IB.build()
            ret = IB.package()
            ret = IB.copy()

