# builds ISO's

import argparse

from empanadas.common import *
from empanadas.util import IsoBuild

parser = argparse.ArgumentParser(description="ISO Artifact Builder")

parser.add_argument('--release', type=str, help="Major Release Version", required=True)
parser.add_argument('--s3', action='store_true', help="S3")
parser.add_argument('--arch', type=str, help="Architecture")
parser.add_argument('--local-compose', action='store_true', help="Compose Directory is Here")
parser.add_argument('--force-download', action='store_true', help="Force a download")
parser.add_argument('--s3-region', type=str, help="S3 region (overrides defaults)")
parser.add_argument('--s3-bucket', type=str, help="S3 bucket name (overrides defaults)")
parser.add_argument('--s3-bucket-url', type=str, help="S3 bucket url (overrides defaults)")
parser.add_argument('--logger', type=str)
results = parser.parse_args()
rlvars = rldict[results.release]
major = rlvars['major']

a = IsoBuild(
        rlvars,
        config,
        major=major,
        s3=results.s3,
        arch=results.arch,
        force_download=results.force_download,
        compose_dir_is_here=results.local_compose,
        s3_region=results.s3_region,
        s3_bucket=results.s3_bucket,
        s3_bucket_url=results.s3_bucket_url,
        logger=results.logger,
)

def run():
    a.run_pull_generic_images()
