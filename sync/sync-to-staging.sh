#!/bin/bash

# Source common variables
# shellcheck disable=SC2046,1091,1090
source "$(dirname "$0")/common"

# Major Version (eg, 8)
MAJ=${1}
# Short name (eg, NFV, extras, Rocky, gluster9)
SHORT=${2}
# The directory where we're going to, usually MAJOR.MINOR, sometimes it's MAJOR.MINOR-RCX
REV=${3}

cd "/mnt/compose/${MAJ}/latest-${SHORT}-${MAJ}" || { echo "Failed to change directory"; ret_val=1; exit 1; }
ret_val=$?

if [ $ret_val -eq "0" ]; then
  TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}"
  mkdir -p "${TARGET}"
  # disabling because none of our files should be starting with dashes. If they
  # are something is *seriously* wrong here.
  # shellcheck disable=SC2035
  sudo -l && find **/* -maxdepth 0 -type d | parallel --will-cite -j 18 sudo rsync -av --chown=10004:10005 --progress --relative --human-readable \
      {} "${TARGET}"
fi
