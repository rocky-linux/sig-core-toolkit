# Builds an image given a version, type, variant, and architecture
# Defaults to the running host's architecture

import argparse
import datetime
import os
import tempfile
import pathlib

from jinja2 import Environment, FileSystemLoader, Template
from typing import List, Tuple

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

results = parser.parse_args()
rlvars = rldict[results.version]
major = rlvars["major"]

STORAGE_DIR = pathlib.Path("/var/lib/imagefactory/storage")
KICKSTART_PATH = pathlib.Path(os.environ.get("KICKSTART_PATH", "/kickstarts"))
BUILDTIME = datetime.datetime.utcnow()


def render_icicle_template(template: Template, architecture: Architecture) -> str:
    handle, output = tempfile.mkstemp()
    if not handle:
        exit(3)
    with os.fdopen(handle, "wb") as tmp:
        _template = template.render(
            architecture=architecture,
            fedora_version=rlvars["fedora_release"],
            iso8601date=BUILDTIME.strftime("%Y%m%d"),
            installdir="kickstart" if results.kickstartdir else "os",
            major=major,
            release=results.release if results.release else 0,
            size="10G",
            type=results.type.capitalize(),
            utcnow=BUILDTIME,
            version_variant=rlvars["revision"] if not results.variant else f"{rlvars['revision']}-{results.variant.capitalize()}",
        )
        tmp.write(_template.encode())
    return output


def generate_kickstart_imagefactory_args(debug: bool = False) -> str:
    type_variant = results.type if not results.variant else f"{results.type}-{results.variant}" # todo -cleanup
    kickstart_path = pathlib.Path(f"{KICKSTART_PATH}/Rocky-{major}-{type_variant}.ks")

    if not kickstart_path.is_file():
        print(f"Kickstart file is not available: {kickstart_path}")
        if not debug:
            exit(2)

    return f"--file-parameter install_script {kickstart_path}"

def get_image_format(_type: str) -> str:
    mapping = {
            "Container": "docker"
    }
    return mapping[_type] if _type in mapping.keys() else ''

def generate_imagefactory_commands(tdl_template: Template, architecture: Architecture) -> List[List[str]]:
    template_path = render_icicle_template(tdl_template, architecture)
    if not template_path:
        exit(2)

    args_mapping = {
        "debug": "--debug" 
    }

    # only supports boolean flags right now?
    args = [param for name, param in args_mapping.items() if getattr(results,name)]
    package_args = []

    kickstart_arg = generate_kickstart_imagefactory_args(True) # REMOVE DEBUG ARG

    if results.type == "Container":
        args += ["--parameter", "offline_icicle", "true"]
        package_args += ["--parameter", "compress", "xz"]
        tar_command = ["tar", "-Oxf", f"{STORAGE_DIR}/*.body" "./layer.tar"]

    type_variant = results.type if not results.variant else f"{results.type}-{results.variant}" # todo -cleanup
    outname = f"Rocky-{rlvars['major']}-{type_variant}.{BUILDTIME.strftime('%Y%m%d')}.{results.release if results.release else 0}.{architecture}"

    outdir = pathlib.Path(f"/tmp/{outname}")

    build_command = (f"imagefactory base_image {kickstart_arg} {' '.join(args)} {template_path}"
                        f" | tee -a {outdir}/logs/base_image-{outname}.out"
                        f" | tail -n4 > {outdir}/base.meta || exit 2" 
            )


    out_type = get_image_format(results.type)
    package_command = ["imagefactory", "target_image", *args, template_path,
                        "--id", "$(awk '$1==\"UUID\":{print $NF}'"+f" /tmp/{outname}/base.meta)",
                        *package_args, 
                        "--parameter", "repository", outname, out_type,
                        "|", "tee", "-a", f"{outdir}/base_image-{outname}.out",
                        "|", "tail", "-n4", ">", f"{outdir}/target.meta", "||", "exit", "3" 
            ]

    copy_command = (f"aws s3 cp --recursive {outdir}/ s3://resf-empanadas/buildimage-{ outname }/{ BUILDTIME.strftime('%s') }/"
        )
    commands = [build_command, package_command, copy_command]
    return commands
    
def run():
    result, error = valid_type_variant(results.type, results.variant)
    if not result:
        print(error)
        exit(2)

    file_loader = FileSystemLoader(f"{_rootdir}/templates")
    tmplenv = Environment(loader=file_loader)
    tdl_template = tmplenv.get_template('icicle/tdl.xml.tmpl')
    job_template = tmplenv.get_template('kube/Job.tmpl')

    for architecture in rlvars["allowed_arches"]:
        architecture = Architecture.New(architecture, major)

        commands = generate_imagefactory_commands(tdl_template, architecture)

        print(job_template.render(
            architecture=architecture,
            backoffLimit=4,
            buildTime=datetime.datetime.utcnow().strftime("%s"),
            command=commands,
            imageName="ghcr.io/neilhanlon/sig-core-toolkit:latest",
            jobname="buildimage",
            namespace="empanadas",
            major=major,
            restartPolicy="Never",
        ))

