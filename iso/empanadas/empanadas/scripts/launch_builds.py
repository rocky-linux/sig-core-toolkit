# Launches the builds of ISOs

import argparse
import datetime

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

    command = ["build-iso", "--release", f"{results.release}", "--rc", "--isolation", "simple"]

    out = ""
    for arch in arches:
        out += job_template.render(
            architecture=arch,
            backoffLimit=4,
            buildTime=datetime.datetime.utcnow().strftime("%s"),
            command=command,
            imageName="ghcr.io/neilhanlon/sig-core-toolkit:latest",
            namespace="empanadas",
            major=major,
            restartPolicy="Never",
        )

    print(out)
