#!/bin/bash
# Syncs everything from staging to production

# Source common variables
# shellcheck disable=SC2046,1091,1090
source "$(dirname "$0")/common"

REV=${REVISION}${APPEND_TO_DIR}

cd "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}" || { echo "Failed to change directory"; ret_val=1; exit 1; }
ret_val=$?

if [ $ret_val -eq "0" ]; then
  TARGET="${PRODUCTION_ROOT}/${CATEGORY_STUB}/${REV:0:3}"
  mkdir -p "${TARGET}"
  # disabling because none of our files should be starting with dashes. If they
  # are something is *seriously* wrong here.
  # shellcheck disable=SC2035
  sudo -l && find ./ -mindepth 1 -maxdepth 1 -type d -exec find {}/ -mindepth 1 -maxdepth 1 -type d \;|sed 's/^..//g' | parallel --will-cite -j 18 sudo rsync -av --chown=10004:10005 --progress --relative --human-readable --delete \
      {} "${TARGET}"
  # shellcheck disable=SC2035
  sudo -l && find ** -maxdepth 0 -type l | parallel --will-cite -j 18 sudo rsync -av --chown=10004:10005 --progress --relative --human-readable \
      {} "${TARGET}"

  # Temporary until empanadas has this support
  if [ -f "COMPOSE_ID" ]; then
    cp COMPOSE_ID "${TARGET}"
    chown 10004:10005 "${TARGET}/COMPOSE_ID"
  fi

  if [ -d "metadata" ]; then
    rsync -av --chown=10004:10005 --progress --relative --human-readable metadata "${TARGET}"
  fi

  # Full file list update for production root
  cd "${PRODUCTION_ROOT}/${CATEGORY_STUB}/" || { echo "Failed to change directory"; exit 1; }
  ## Hardlink everything except xml files
  echo "Hard linking"
  hardlink -x '.*\.xml.*' "${REVISION}"
  echo "Syncing to prod completed. Please run the file list script."
fi
