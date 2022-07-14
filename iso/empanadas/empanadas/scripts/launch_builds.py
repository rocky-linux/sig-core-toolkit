# Launches the builds of ISOs

import argparse
import datetime

from empanadas.common import *
from empanadas.common import _rootdir

from jinja2 import Environment, FileSystemLoader

parser = argparse.ArgumentParser(description="Generate Kubernetes Jobs to run lorax in mock and upload the result. Pipe into kubectl for the appropriate cluster")

parser.add_argument('--release', type=str, help="Major Release Version: (8|9)", required=True)
parser.add_argument('--env', type=str, help="environment: one of (eks|ext|all). presently jobs are scheduled on different kubernetes clusters", required=True)
parser.add_argument('--rc', action='store_true', help="Release Candidate, Beta, RLN")
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

    command = ["build-iso", "--release", f"{results.release}", "--isolation", "simple", "--hashed"]
    if results.rc:
        command += ["--rc"]

    buildstamp = datetime.datetime.utcnow()

    out = ""
    for architecture in arches:
        copy_command = (f"aws s3 cp --recursive --exclude=* --include=lorax* "
                            f"/var/lib/mock/rocky-{ major }-$(uname -m)/root/builddir/ "
                            f"s3://resf-empanadas/buildiso-{ major }-{ architecture }/{ buildstamp.strftime('%s') }/"
        )
        out += job_template.render(
            architecture=architecture,
            backoffLimit=4,
            buildTime=buildstamp.strftime("%s"),
            command=[command, copy_command],
            imageName="ghcr.io/rocky-linux/sig-core-toolkit:latest",
            jobname="buildiso",
            namespace="empanadas",
            major=major,
            restartPolicy="Never",
        )

    print(out)
