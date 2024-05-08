"""Build an image with a given backend"""

import datetime
import logging
import os
import pathlib

from attrs import define, field

from empanadas.backends import BackendInterface, KiwiBackend
from empanadas.common import Architecture
from empanadas.common import _rootdir
from . import utils

from jinja2 import Environment, FileSystemLoader, Template
from typing import List, Optional, Tuple, Callable


@define(kw_only=True)
class ImageBuild:  # pylint: disable=too-few-public-methods
    """Image builder using a given backend"""
    tmplenv: Environment = field(init=False)

    # Only things we know we're keeping in this class here
    architecture: Architecture = field()
    backend: BackendInterface = field()
    build_time: datetime.datetime = field()
    debug: bool = field(default=False)
    log: logging.Logger = field()
    release: int = field(default=0)
    timeout: str = field(default='3600')

    image_type: str = field()  # the type of the image
    type_variant: str = field(init=False)
    variant: Optional[str] = field()

    # Kubernetes job template
    job_template: Optional[Template] = field(init=False)  # the kube Job tpl

    # Commands to stage artifacts

    # Where the artifacts should go to
    outdir: pathlib.Path = field(init=False)
    outname: str = field(init=False)

    def __attrs_post_init__(self):
        self.backend.ctx = self

        file_loader = FileSystemLoader(f"{_rootdir}/templates")
        self.tmplenv = Environment(loader=file_loader)

        self.job_template = self.tmplenv.get_template('kube/Job.tmpl')

        self.type_variant = self.type_variant_name()
        self.outdir, self.outname = self.output_name()

    def output_name(self) -> Tuple[pathlib.Path, str]:
        directory = f"Rocky-{self.architecture.major}-{self.type_variant}-{self.architecture.version}-{self.build_time.strftime('%Y%m%d')}.{self.release}"
        name = f"{directory}.{self.architecture.name}"
        outdir = pathlib.Path("/tmp/", directory)
        return outdir, name

    def type_variant_name(self):
        return self.image_type if not self.variant else f"{self.image_type}-{self.variant}"

    def prepare_and_run(self, command: utils.CMD_PARAM_T, search: Callable = None) -> utils.CMD_RESULT_T:
        return utils.runCmd(self, self.prepare_command(command), search)

    def prepare_command(self, command_list: utils.CMD_PARAM_T) -> List[str]:
        """
        Commands may be a callable, which should be a lambda to be evaluated at
        preparation time with available locals. This can be used to, among
        other things, perform lazy evaluations of f-strings which have values
        not available at assignment time. e.g., filling in a second command
        with a value extracted from the previous step or command.
        """

        r = []
        for c in command_list:
            if callable(c) and c.__name__ == '<lambda>':
                r.append(c())
            else:
                r.append(str(c))
        return r

    def render_kubernetes_job(self):
        # TODO(neil): should this be put in the builder class itself to return the right thing for us?
        if self.backend == KiwiBackend:
            self.log.error("Kube not implemented for Kiwi")

        commands = [self.backend.build_command(), self.backend.package_command(), self.backend.copy_command()]
        if not self.job_template:
            return None
        template = self.job_template.render(
                architecture=self.architecture.name,
                backoffLimit=4,
                buildTime=self.build_time.strftime("%s"),
                command=commands,
                imageName="ghcr.io/rockylinux/sig-core-toolkit:latest",
                jobname="buildimage",
                namespace="empanadas",
                major=self.architecture.major,
                minor=self.architecture.minor,
                restartPolicy="Never",
            )
        return template

    def upload(self, skip=False) -> int:
        if not skip:
            self.log.info("Copying files to output directory")
            copy_command = ["aws", "s3", "cp", "--recursive", f"{self.outdir}/",
                            f"s3://resf-empanadas/buildimage-{self.architecture.version}-{self.architecture.name}/{self.outname}/{self.build_time.strftime('%s')}/"
                            ]
            ret, out, err, _ = self.prepare_and_run(copy_command, search=False)
            return ret

        self.ctx.log.info(f"Build complete! Output available in {self.ctx.outdir}/")
        return 0
