#!/bin/bash
# Syncs everything from staging to production

# Source common variables
source $(dirname "$0")/common

REV=${1}

cd "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}"
ret_val=$?

if [ $ret_val -eq "0" ]; then
  TARGET="${PRODUCTION_ROOT}/${CATEGORY_STUB}/${REV:0:3}"
  mkdir -p "${TARGET}"
  sudo -l && find **/* -maxdepth 0 -type d | parallel --will-cite -j 18 sudo rsync -av --chown=10004:10005 --progress --relative --human-readable \
      {} ${TARGET}
else
  echo "Failed to change directory"
fi
