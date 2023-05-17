#!/bin/bash

# Short name (eg, NFV, extras, Rocky, gluster9)
SHORT=${1}

# Source common variables
# shellcheck disable=SC2046,1091,1090
source "$(dirname "$0")/common"

if [[ $# -eq 0 ]]; then
  echo "You must specify a short name."
  exit 1
fi

if [[ "${RLVER}" -ne "8" ]]; then
  echo "This is only used for Rocky Linux 8 releases."
fi

# Major Version (eg, 8)
MAJ=${RLVER}

#cd "${RELEASE_COMPOSE_ROOT}/compose" || { echo "Failed to change directory"; ret_val=1; exit 1; }
cd "${RELEASE_COMPOSE_ROOT}/" || { echo "Failed to change directory"; ret_val=1; exit 1; }
ret_val=$?

if [ $ret_val -eq "0" ]; then
  TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}"
  # The target should already exist as this is used to do simple syncs.
  mkdir -p "${TARGET}"

  # Find all directories for this compose
  repo_dirs=( $(find compose -name repodata -type d | sed 's/compose\///g') )

  # Delete all repodata for this compose
  for x in "${repo_dirs[@]}"; do
    test -d "${TARGET}/${x}"
    ret_val=$?
    if [ $ret_val -eq "0" ]; then
      /bin/rm "${TARGET:?}/${x}/"*
    else
      echo "${x} not found"
    fi
  done

  # We need to delete the old repodata
  rsync_no_delete_staging_pungi "${TARGET}"
  echo "Hardlinking staging directory (${TARGET})"
  perform_hardlink "${TARGET}"
fi
