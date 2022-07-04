# Builds an image given a version, type, variant, and architecture
# Defaults to the running host's architecture

import argparse
import datetime
import json
import logging
import subprocess
import sys
import time
import os
import tempfile
import pathlib
import platform

from botocore import args
from attrs import define, Factory, field, asdict

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

@define(kw_only=True)
class ImageBuild:
    architecture: Architecture = field()
    base_uuid: Optional[str] = field(default="")
    command_args: List[str] = field(factory=list)
    common_args: List[str] = field(factory=list)
    debug: bool = field(default=False)
    image_type: str = field()
    job_template: Optional[Template] = field(init=False)
    kickstart_arg: List[str] = field(factory=list)
    out_type: str = field(init=False)
    outdir: pathlib.Path = field(init=False) 
    outname: str = field(init=False)
    package_args: List[str] = field(factory=list)
    target_uuid: Optional[str] = field(default="")
    tdl_path: pathlib.Path = field(init=False)
    template: Template = field()
    type_variant: str = field(init=False) 
    stage_commands: Optional[List[List[Union[str,Callable]]]] = field(init=False)
    variant: Optional[str] = field()
    revision: Optional[int] = field()
    metadata: pathlib.Path = field(init=False)
    fedora_release: int = field()

    def __attrs_post_init__(self):
        self.tdl_path = self.render_icicle_template()
        if not self.tdl_path:
            exit(2)
        self.type_variant = self.type_variant_name()
        self.outname = self.output_name()
        self.outdir = pathlib.Path(f"/tmp/{self.outname}")
        self.out_type = self.image_format()
        self.command_args = self._command_args()
        self.package_args = self._package_args()
        self.common_args = self._common_args()
        self.kickstart_arg = self.kickstart_imagefactory_args()

        self.metadata = pathlib.Path(self.outdir, "metadata.json")

        if self.image_type == "Container":
            self.stage_commands = [
                    ["tar", "-C", f"{self.outdir}", "--strip-components=1", "-x", "-f", lambda: f"{STORAGE_DIR}/{self.target_uuid}.body", "*/layer.tar"]
            ]
        if self.image_type == "GenericCloud":
            self.stage_commands = [
                    ["qemu-img", "convert", "-f", "raw", "-O", "qcow2", lambda: f"{STORAGE_DIR}/{self.target_uuid}.body", f"{self.outdir}/{self.outname}.qcow2"]
            ]

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

    def output_name(self):
        return f"Rocky-{self.architecture.version}-{self.type_variant}.{BUILDTIME.strftime('%Y%m%d')}.{results.release if results.release else 0}.{self.architecture.name}"
    
    def type_variant_name(self):
        return self.image_type if not self.variant else f"{self.image_type}-{self.variant.capitalize()}"

    def _command_args(self):
        args_mapping = {
            "debug": "--debug" 
        }
        return [param for name, param in args_mapping.items() if getattr(results,name)]

    def _package_args(self) -> List[str]:
        if results.type == "Container":
            return ["--parameter", "compress", "xz"]
        return [""]

    def _common_args(self) -> List[str]:
        args = []
        if self.image_type == "Container":
            args = ["--parameter", "offline_icicle", "true"]
        if self.image_type == "GenericCloud":
            args = ["--parameter", "generate_icicle", "false"]
        return args

    def image_format(self) -> str:
        mapping = {
                "Container": "docker"
        }
        return mapping[self.image_type] if self.image_type in mapping.keys() else ''

    def kickstart_imagefactory_args(self) -> List[str]:
        kickstart_path = pathlib.Path(f"{KICKSTART_PATH}/Rocky-{self.architecture.version}-{self.type_variant}.ks")

        if not kickstart_path.is_file():
            log.warn(f"Kickstart file is not available: {kickstart_path}")
            if not debug:
                log.warn("Exiting because debug mode is not enabled.")
                exit(2)

        return ["--file-parameter", "install_script", str(kickstart_path)]

    def render_icicle_template(self) -> pathlib.Path:
        handle, output = tempfile.mkstemp()
        if not handle:
            exit(3)
        with os.fdopen(handle, "wb") as tmp:
            _template = self.template.render(
                architecture=self.architecture.name,
                fedora_version=self.fedora_release,
                iso8601date=BUILDTIME.strftime("%Y%m%d"),
                installdir="kickstart" if results.kickstartdir else "os",
                major=self.architecture.version,
                release=results.release if results.release else 0,
                size="10G",
                type=self.image_type,
                utcnow=BUILDTIME,
                version_variant=self.revision if not self.variant else f"{self.revision}-{self.variant}",
            )
            tmp.write(_template.encode())
            tmp.flush()
        return pathlib.Path(output)

    def build_command(self) -> List[str]:
        build_command = ["imagefactory", *self.command_args, "base_image", *self.common_args, *self.kickstart_arg, self.tdl_path
                            # "|", "tee", "-a", f"{outdir}/logs/base_image-{outname}.out",
                            # "|", "tail", "-n4", ">", f"{outdir}/base.meta", "||", "exit", "2"
                        ]
        return build_command
    def package_command(self) -> List[str]:
        package_command = ["imagefactory", *self.command_args, "target_image", self.out_type, *self.common_args,
                            "--id", f"{self.base_uuid}",
                            *self.package_args, 
                            "--parameter", "repository", self.outname,
                            # "|", "tee", "-a", f"{outdir}/base_image-{outname}.out",
                            # "|", "tail", "-n4", ">", f"{outdir}/target.meta", "||", "exit", "3" 
                ]
        return package_command

    def copy_command(self) -> List[str]:

        copy_command = ["aws", "s3", "cp", "--recursive", f"{self.outdir}/", f"s3://resf-empanadas/buildimage-{ self.outname }/{ BUILDTIME.strftime('%s') }/"]

        return copy_command

    def build(self) -> int:
        if self.base_uuid:
            return 0

        ret, out, err, uuid = self.runCmd(self.build_command()) 
        if ret > 0:
            #error in build command
            log.error("Problem during build.")
        if not uuid:
            log.error("Build UUID not found in stdout. Dumping stdout and stderr")
            self.log_subprocess(ret, out, err)
            return ret
        self.base_uuid = uuid.rstrip()
        self.save()
        return ret

    def package(self) -> int: 
        # Some build types don't need to be packaged by imagefactory
        if self.image_type == "GenericCloud":
            self.target_uuid = self.base_uuid if hasattr(self, 'base_uuid') else ""

        if self.target_uuid:
            return 0

        ret, out, err, uuid = self.runCmd(self.package_command())
        if ret > 0:
            log.error("Problem during packaging")
        if not uuid:
            log.error("Target Image UUID not found in stdout. Dumping stdout and stderr")
            self.log_subprocess(ret, out, err)
            return ret
        self.target_uuid = uuid.rstrip()
        self.save()
        return ret

    def stage(self) -> int:
        """ Stage the artifacst from wherever they are (unpacking and converting if needed)"""
        if not self.stage_commands:
            return 0

        returns = []
        for command in self.stage_commands:
            ret, out, err, _ = self.runCmd(command, search=False)
            if ret > 0:
                log.error("Problem during unpack.")
                self.log_subprocess(ret, out, err)
            returns.append(ret)

        return all(ret > 0 for ret in returns)

    def copy(self) -> int:
        # move or unpack if necessary
        if (stage := self.stage() > 0):
            raise Exception(stage)

        ret, out, err, _ = self.runCmd(self.copy_command(), search=False) 
        if ret > 0:
            #error in build command
            log.error("Problem during build.")
        return ret

    def runCmd(self, command: List[Union[str, Callable]], search: bool = True) -> Tuple[int, Union[IO[bytes],None], Union[IO[bytes],None], Union[str,None]]:
        prepared, _ = self.prepare_command(command)
        log.info(f"Running command: {' '.join(prepared)}")

        kwargs = {
            "stderr": subprocess.PIPE,
            "stdout": subprocess.PIPE
        }
        if debug: del kwargs["stderr"]

        with subprocess.Popen(prepared,  **kwargs) as p:
            uuid = None
            if search:
                for _, line in enumerate(p.stdout): # type: ignore
                    ln = line.decode()
                    if ln.startswith("UUID: "):
                        uuid = ln.split(" ")[-1]
                        log.debug(f"found uuid: {uuid}")
            return p.wait(), p.stdout, p.stdin, uuid

    def prepare_command(self, command_list: List[Union[str, Callable]]) -> Tuple[List[str],List[None]]:
        """
        Commands may be a callable, which should be a lambda to be evaluated at
        preparation time with available locals. This can be used to, among
        other things, perform lazy evaluations of f-strings which have values
        not available at assignment time. e.g., filling in a second command
        with a value extracted from the previous step or command.

        """

        r = []
        return r, [r.append(c()) if (callable(c) and c.__name__ == '<lambda>') else r.append(str(c)) for c in command_list]

    def log_subprocess(self, return_code: int, stdout: Union[IO[bytes], None], stderr: Union[IO[bytes], None]):
        def log_lines(title, lines):
            log.info(f"====={title}=====")
            for _, line in lines:
                log.info(line.decode())
        log.info(f"Command return code: {return_code}")
        log_lines("Command STDOUT", enumerate(stdout)) # type: ignore
        log_lines("Command STDERR", enumerate(stderr)) # type: ignore

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
        with open(pathlib.Path(self.outdir, "metadata.json"), "w") as f:
            o = { name: getattr(self, name) for name in ["base_uuid", "target_uuid"] }
            log.debug(o)
            json.dump(o, f)

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
                image_type=results.type, 
                variant=results.variant,
                architecture=Architecture.New(architecture, major),
                template=tdl_template,
                revision=rlvars['revision'],
                fedora_release=rlvars['fedora_release'],
                debug=True
        )
        if results.kube:
            IB.job_template = tmplenv.get_template('kube/Job.tmpl')
            #commands = IB.kube_commands()
            print(IB.render_kubernetes_job())
        else:
            ret = IB.build()
            ret = IB.package()
            ret = IB.copy()


