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

# Major Version (eg, 8)
MAJ=${RLVER}

cd "${RELEASE_COMPOSE_ROOT}/compose" || { echo "Failed to change directory"; ret_val=1; exit 1; }
ret_val=$?

if [ $ret_val -eq "0" ]; then
  TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}"
  mkdir -p "${TARGET}"
  # disabling because none of our files should be starting with dashes. If they
  # are something is *seriously* wrong here.
  # shellcheck disable=SC2035
  sudo -l && find **/* -maxdepth 0 -type d | parallel --will-cite -j 18 sudo rsync -av --chown=10004:10005 --progress --relative --human-readable --delete \
      {} "${TARGET}"

  # This is temporary until we implement rsync into empanadas
  if [ -f "COMPOSE_ID" ]; then
    cp COMPOSE_ID "${TARGET}"
    chown 10004:10005 "${TARGET}/COMPOSE_ID"
  fi

  if [ -d "metadata" ]; then
    rsync -av --chown=10004:10005 --progress --relative --human-readable metadata "${TARGET}"
  fi
fi
