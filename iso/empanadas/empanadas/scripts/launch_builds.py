# Launches the builds of ISOs

import argparse

from empanadas.common import *
from empanadas.common import _rootdir

from jinja2 import Environment, FileSystemLoader

parser = argparse.ArgumentParser(description="ISO Compose")

parser.add_argument('--release', type=str, help="Major Release Version", required=True)
parser.add_argument('--env', type=str, help="environment", required=True)
results = parser.parse_args()
rlvars = rldict[results.release]
major = rlvars['major']

EXTARCH=["s390x", "ppc64le"]
EKSARCH=["amd64", "arm64"]

def run():
    file_loader = FileSystemLoader(f"{_rootdir}/templates")
    tmplenv = Environment(loader=file_loader)
    job_template = tmplenv.get_template('kube/Job.tmpl')

    arches = EKSARCH
    if results.env == "ext" and results.env != "all":
        arches = EXTARCH
    elif results.env == "all":
        arches = EKSARCH+EXTARCH

    out = ""
    for arch in arches:
        out += job_template.render(
            architecture=arch,
            backoffLimit=4,
            command=["build-iso", "--release", "9", "--rc", "--isolation", "simple"],
            containerName=f"buildiso-{major}-{arch}",
            imageName="ghcr.io/neilhanlon/sig-core-toolkit:latest",
            jobName=f"build-iso-{arch}",
            namespace="empanadas",
            major=major,
            restartPolicy="Never",
        )

    print(out)
