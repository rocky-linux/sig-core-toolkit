#!/usr/bin/env python3
# This is copied into peridot-releng and ran. This file is likely temporary
# until we decide if this goes into that git repo.
import argparse
import os
import json

from catalog import (
    PeridotCatalogSync,
    PeridotCatalogSyncPackage,
    PeridotCatalogSyncPackageType,
    PeridotCatalogSyncRepository,
)

def main(prepopulate: str, output_path: str, major: int, minor: int):
    print(f"Using prepopulate file: {prepopulate}")

    with open(prepopulate) as json_file:
        prepop = json.load(json_file)
        json_file.close()

    # Create a catalog
    catalog = PeridotCatalogSync()
    catalog.major = major
    catalog.minor = minor

    # Create indexes
    package_index = {}
    repo_module_index = {}
    module_name_index = {}
    module_defaults = []

    # Read prepopulate json and create package objects
    all_arches = []
    for repo in prepop.keys():
        for arch in prepop[repo].keys():
            if arch not in all_arches:
                all_arches.append(arch)
            for package in prepop[repo][arch].keys():
                if package not in package_index:
                    package_index[package] = {}
                if repo not in package_index[package]:
                    package_index[package][repo] = {
                        "include_filter": [],
                        "multilib": [],
                    }
                na_list = prepop[repo][arch][package]
                for na in na_list:
                    splitted = na.split(".")
                    arch_package = splitted[len(splitted) - 1]
                    if arch != arch_package and arch_package != "noarch":
                        if arch not in package_index[package][repo]["multilib"]:
                            package_index[package][repo]["multilib"].append(arch)
                    if na not in package_index[package][repo]["include_filter"]:
                        package_index[package][repo]["include_filter"].append(na)

    arch_specific_excludes = {}
    na_index = {}
    for pkg in package_index.keys():
        for repo in package_index[pkg].keys():
            na_list = list(
                filter(
                    lambda x: x.endswith(".noarch"),
                    package_index[pkg][repo]["include_filter"],
                )
            )
            if not na_list:
                continue
            exclude_arches = {}
            for na in na_list:
                for arch in all_arches:
                    if (
                        arch not in prepop[repo]
                        or pkg not in prepop[repo][arch]
                        or na not in prepop[repo][arch][pkg]
                    ):
                        if na not in exclude_arches:
                            exclude_arches[na] = []
                        exclude_arches[na].append(arch)
                na_index[na] = na
            if not exclude_arches:
                continue
            if pkg not in arch_specific_excludes:
                arch_specific_excludes[pkg] = {}
            if repo not in arch_specific_excludes[pkg]:
                arch_specific_excludes[pkg][repo] = []
            arch_specific_excludes[pkg][repo].append(exclude_arches)

    # Index arch specific excludes by repo and arch
    repo_arch_index = {}
    for pkg in arch_specific_excludes.keys():
        for repo in arch_specific_excludes[pkg].keys():
            if repo not in repo_arch_index:
                repo_arch_index[repo] = {}
            for arches2 in arch_specific_excludes[pkg][repo]:
                for na in arches2.keys():
                    for arch in arches2[na]:
                        if arch not in repo_arch_index[repo]:
                            repo_arch_index[repo][arch] = []
                        if na not in repo_arch_index[repo][arch]:
                            repo_arch_index[repo][arch].append(na)

    # Add noarch packages not in a specific arch to exclude filter
    for repo in repo_arch_index.keys():
        repo_key = f"^{repo}$"
        filter_tuple = {}
        for arch in repo_arch_index[repo].keys():
            if arch not in filter_tuple:
                filter_tuple[arch] = []
            for na in repo_arch_index[repo][arch]:
                na = na.removesuffix(".noarch")
                if na not in filter_tuple[arch]:
                    filter_tuple[arch].append(na)
        catalog.exclude_filter.append((repo_key, filter_tuple))

    for package in package_index.keys():
        package_type = PeridotCatalogSyncPackageType.PACKAGE_TYPE_NORMAL_FORK
        if package in module_name_index:
            package_type = PeridotCatalogSyncPackageType.PACKAGE_TYPE_NORMAL_FORK_MODULE
        elif package.startswith("rocky-"):
            package_type = PeridotCatalogSyncPackageType.PACKAGE_TYPE_NORMAL_SRC

        catalog.add_package(
            PeridotCatalogSyncPackage(
                package,
                package_type,
                [
                    PeridotCatalogSyncRepository(
                        x,
                        package_index[package][x]["include_filter"],
                        package_index[package][x]["multilib"],
                        (get_modules_for_repo(package, x, repo_module_index) if x in repo_module_index else None) if package in module_name_index else None,
                    )
                    for x in package_index[package].keys()
                ],
            )
        )

    print(f"Found {len(catalog.packages)} packages")

    f = open(output_path, "w")
    f.write(catalog.to_prototxt())
    f.close()

    print(f"Catalog written to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a catalog from a standalone prepopulate.json"
    )
    parser.add_argument("--prepopulate-path", type=str, required=True)
    parser.add_argument("--major", type=int, required=True)
    parser.add_argument("--minor", type=int, required=True)
    parser.add_argument("--output-path", type=str, default="hidden.cfg")
    args = parser.parse_args()
    main(args.prepopulate_path, args.output_path, args.major, args.minor)
