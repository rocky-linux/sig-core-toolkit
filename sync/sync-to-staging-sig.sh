#!/bin/bash

# Source common variables
# shellcheck disable=SC2046,1091,1090
source "$(dirname "$0")/common"

if [[ $# -eq 0 ]]; then
  echo "Not enough information."
  echo "You must use: sig"
  exit 1
fi

# Major Version (eg, 8)
MAJ=${RLVER}
# Short name (eg, NFV, extras, Rocky, gluster9)
SHORT=${1}
# Note, this should be lowercase. eg, storage.
SIG=${2}

cd "/mnt/compose/${MAJ}/latest-SIG-${SHORT}-${MAJ}/compose" || { echo "Failed to change directory"; ret_val=1; exit 1; }
ret_val=$?

if [ $ret_val -eq "0" ]; then
  TARGET=${STAGING_ROOT}/${SIG_CATEGORY_STUB}/
  mkdir -p "${TARGET}"
  # disabling because none of our files should be starting with dashes. If they
  # are something is *seriously* wrong here.
  # shellcheck disable=SC2035
  sudo -l && find **/* -maxdepth 0 -type d | parallel --will-cite -j 18 sudo rsync -av --chown=10004:10005 --progress --relative --human-readable --delete \
      {} "${TARGET}"
fi
