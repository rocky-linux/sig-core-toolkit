#!/usr/bin/env python3
#
# quick-bump.py - Quickly bumps a release version for a rebuild. This is mostly
#                 used in cases of */src/* package rebuilds like for SIG's. It
#                 should be rare that the base distribution needs this.

import os
import subprocess
import sys
import argparse
import shutil

parser = argparse.ArgumentParser()
parser.add_argument(
    "--pkg", help="Package name to bump (can be comma delimited list)", required=True
)
parser.add_argument("--branch", help="Package branch", required=True)
parser.add_argument("--sig", help="Name of SIG that holds this package")
parser.add_argument(
    "--peridot-import",
    help="Tell peridot to import",
    required=False,
    action="store_true",
)
parser.add_argument(
    "--peridot-endpoint",
    help="Peridot API Endpoint (PERIDOT_ENDPOINT)",
    required=False,
    default="peridot-api.build.resf.org",
)
parser.add_argument(
    "--peridot-hdr-endpoint",
    help="Peridot HDR Endpoint (PERIDOT_HDR_ENDPOINT)",
    required=False,
    default="hdr.build.resf.org",
)
parser.add_argument(
    "--peridot-project-id",
    help="Peridot project ID (PERIDOT_PROJECT_ID)",
    required=False,
)
parser.add_argument(
    "--peridot-client-id", help="Peridot client ID (PERIDOT_CLIENT_ID)", required=False
)
parser.add_argument(
    "--peridot-client-secret",
    help="Peridot client secret (PERIDOT_CLIENT_SECRET)",
    required=False,
)
parser.add_argument(
    "--dry", help="Do a dry bump for testing", required=False, action="store_true"
)
parser.add_argument(
    "--rightmost",
    help="see rpmdev-bumpspec; noop with --string",
    required=False,
    action="store_true",
)
parser.add_argument(
    "--string", help="see rpmdev-bumpspec; trumps --rightmost", required=False
)

parser.add_argument("--git-user", default="Release Engineering")
parser.add_argument("--git-email", default="releng@rockylinux.org")
parser.add_argument(
    "--url",
    default="ssh://git@git.rockylinux.org:22220/staging/src/{pkg}.git",
    help="override default URL",
)
parser.add_argument(
    "--change-user",
    help="Sets the user for the rpm changelog (first last <email>)",
    default="Release Engineering <releng@rockylinux.org>",
)
parser.add_argument(
    "--change-comment",
    help="Sets the comment that will appear in the changelog and commit message",
    default="Release tag bump for rebuild (https://sig-core.rocky.page/rebuild/)",
)

args = parser.parse_args(args=None if sys.argv[1:] else ["--help"])
user = args.change_user
comment = args.change_comment

if args.peridot_import:
    peridot_api_endpoint = os.environ.get(
        "PERIDOT_ENDPOINT") or args.peridot_endpoint
    peridot_hdr_endpoint = (
        os.environ.get("PERIDOT_HDR_ENDPOINT") or args.peridot_hdr_endpoint
    )
    peridot_project_id = os.environ.get(
        "PERIDOT_PROJECT_ID") or args.peridot_project_id
    peridot_client_id = os.environ.get(
        "PERIDOT_CLIENT_ID") or args.peridot_client_id
    peridot_client_secret = (
        os.environ.get("PERIDOT_CLIENT_SECRET") or args.peridot_client_secret
    )
    print("Peridot import not supported yet")
    sys.exit(1)

if os.geteuid() == 0:
    print("DO NOT RUN AS ROOT")
    sys.exit(1)

if args.sig:
    default_url = "ssh://git@git.rockylinux.org:22220/sig/{sig}/src/{pkg}.git"

if args.url:
    default_url = getattr(args, "url")

rightmost = "--rightmost" if args.rightmost else None
string = f"--string={args.string}" if args.string else ""

extra_args = [arg for arg in (rightmost, string) if arg]

# functions
workdir = "/var/tmp"
environment = os.environ
pkgs = args.pkg.split(",")


def runcmd(cmd, action, package, env, pwd=workdir):
    """
    Runs a command using subprocess and returns 0 or 1
    """
    try:
        subprocess.check_call(cmd, env=env, cwd=pwd)
    except subprocess.CalledProcessError as err:
        sys.stderr.write("%s failed %s: %s\n" % (package, action, err))
        return 1
    return 0


for pkg in pkgs:
    joined_dir = os.path.join(workdir, pkg)
    spec_dir = os.path.join(workdir, pkg, "SPECS")

    checkout_url = default_url.format(pkg=pkg, sig=args.sig)

    print(f"Checking out {checkout_url}")
    gitcmd = ["git", "clone", checkout_url,
              "--branch", args.branch, joined_dir]

    if runcmd(gitcmd, "git clone", pkg, environment):
        continue

    files = os.listdir(spec_dir)
    spec = ""
    for file in files:
        if file.endswith(".spec"):
            spec = os.path.join(spec_dir, file)
            break

    if not spec:
        sys.stderr.write("Failed to find a spec for %s\n" % pkg)
        continue

    print("Bumping release of %s (%s)" % (spec, extra_args))
    bumprel = ["rpmdev-bumpspec", "-D", "-u",
               user, "-c", comment, spec, *extra_args]
    bumprel_old = ["rpmdev-bumpspec", "-u",
                   user, "-c", comment, spec, *extra_args]
    if runcmd(bumprel, "rpmdev-bumpspec", pkg, environment):
        print("Potentially old bumpspec version. Trying again.")
        if runcmd(bumprel_old, "rpmdev-bumpspec", pkg, environment):
            continue

    print("Setting git user and email for this operation")
    git_name = ["git", "config", "user.name", args.git_user]
    git_mail = ["git", "config", "user.email", args.git_email]
    if runcmd(git_name, "git_name", pkg, environment, pwd=joined_dir):
        continue

    if runcmd(git_mail, "git_mail", pkg, environment, pwd=joined_dir):
        continue

    print("Committing changes")
    commit = ["git", "commit", "-asm", comment, "--allow-empty"]
    if runcmd(commit, "commit", pkg, environment, pwd=joined_dir):
        continue

    if not args.dry:
        push = ["git", "push"]
        print("Pushing changes for %s" % pkg)
        if runcmd(push, "push", pkg, environment, pwd=joined_dir):
            continue

        shutil.rmtree(joined_dir)
