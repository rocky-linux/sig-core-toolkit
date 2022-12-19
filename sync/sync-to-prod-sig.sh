#!/bin/bash

# Source common variables
# shellcheck disable=SC2046,1091,1090
source "$(dirname "$0")/common"

#if [[ $# -eq 0 ]] || [[ $# -eq 1 ]]; then
#  echo "Not enough information."
#  echo "You must use: shortname sig"
#  exit 1
#fi

cd "${STAGING_ROOT}/${SIG_CATEGORY_STUB}/${MAJOR}" || { echo "Failed to change directory"; ret_val=1; exit 1; }
ret_val=$?

if [ $ret_val -eq "0" ]; then
  TARGET=${PRODUCTION_ROOT}/${SIG_CATEGORY_STUB}/${MAJOR}/
  mkdir -p "${TARGET}"
  # disabling because none of our files should be starting with dashes. If they
  # are something is *seriously* wrong here.
  # shellcheck disable=SC2035
  sudo -l && find **/* -maxdepth 0 -type d | parallel --will-cite -j 18 sudo rsync -av --chown=10004:10005 --progress --relative --human-readable --delete \
      {} "${TARGET}"

  cd "${PRODUCTION_ROOT}/${SIG_CATEGORY_STUB}/" || { echo "Failed to change directory"; exit 1; }
  echo "Hard linking"
  hardlink -x '.*\.xml.*' "${MAJOR}"
  echo "Syncing to prod completed. Please run the file list script."
fi
