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

if [[ "${RLVER}" -eq "8" ]]; then
  echo "This is only used for Rocky Linux 9+ releases."
  exit 1
fi

# Major Version (eg, 8)
MAJ=${RLVER}

#cd "${RELEASE_COMPOSE_ROOT}/compose" || { echo "Failed to change directory"; ret_val=1; exit 1; }
cd "${RELEASE_COMPOSE_ROOT}/" || { echo "Failed to change directory"; ret_val=1; exit 1; }
ret_val=$?

if [ $ret_val -eq "0" ]; then
  TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}"
  mkdir -p "${TARGET}"
  echo "Hardlinking compose directory before syncing"
  perform_hardlink "compose"
  rsync_delete_staging "${TARGET}"
fi
