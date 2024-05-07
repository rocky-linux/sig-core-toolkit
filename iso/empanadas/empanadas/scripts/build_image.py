# Builds an image given a version, type, variant, anctx.d architecture
# Defaults to the running host's architecture

import argparse
import datetime
import logging
import platform
import sys

from empanadas.common import Architecture, rldict, valid_type_variant
from empanadas.builders import ImageBuild
from empanadas.backends import ImageFactoryBackend, KiwiBackend

parser = argparse.ArgumentParser(description="ISO Compose")

parser.add_argument('--version',
                    type=str, help="Release Version (8.6, 9.1)", required=True)
parser.add_argument('--rc', action='store_true', help="Release Candidate")
parser.add_argument('--kickstartdir', action='store_true',
                    help="Use the kickstart dir instead of the os dir")
parser.add_argument('--debug', action='store_true', help="debug?")
parser.add_argument('--skip', type=str,
                    help="what stage(s) to skip",
                    required=False)
parser.add_argument('--type', type=str,
                    help="Image type (container, genclo, azure, aws, vagrant)",
                    required=True)
parser.add_argument('--variant', type=str, help="", required=False)
parser.add_argument('--release', type=str,
                    help="Image release for builds with the same date stamp",
                    required=False)
parser.add_argument('--kube', action='store_true',
                    help="output as a K8s job(s)",
                    required=False)
parser.add_argument('--timeout', type=str,
                    help="change timeout for imagefactory build process",
                    required=False, default='3600')


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


def run():
    try:
        valid_type_variant(results.type, results.variant)
    except Exception as e:
        log.exception(e)
        exit(2)

    arches = rlvars['allowed_arches'] if results.kube else [platform.uname().machine]

    for architecture in arches:
        if results.type in ["Container", "GenericCloud"]:
            backend = KiwiBackend(
            )
        else:
            backend = ImageFactoryBackend(
                kickstart_dir="kickstart" if results.kickstartdir else "os",
                kickstart_repo=rlvars['livemap']['git_repo']
            )
        IB = ImageBuild(
                architecture=Architecture.from_version(architecture, rlvars['revision']),
                debug=results.debug,
                image_type=results.type,
                release=results.release if results.release else 0,
                variant=results.variant,
                build_time=datetime.datetime.utcnow(),
                backend=backend,
                log=log,
        )

        if results.kube:
            # commands = IB.kube_commands()
            print(IB.render_kubernetes_job())
            sys.exit(0)

        skip_stages = results.skip.split(',') if results.skip else []
        stages = ["prepare", "build", "clean", "stage"]
        for i, stage in enumerate(stages):
            skip_stage = stage in skip_stages

            log.info(f"Stage {i} - {stage}{' SKIP' if skip_stage else ''}")

            if skip_stage:
                continue

            method = getattr(IB.backend, stage)
            if callable(method):
                method()
            else:
                log.fatal(f"Unable to execute {stage}")
