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
  echo "Syncing ${REVISION}"
  sudo -l && time fpsync -n 24 -o '-av --numeric-ids --no-compress --chown=10004:10005' -t /mnt/compose/partitions "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/" "${TARGET}/"

  # Full file list update for production root
  cd "${PRODUCTION_ROOT}/" || { echo "Failed to change directory"; exit 1; }
  echo "Getting a full file list for the root dir"
  find . > fullfilelist
  if [[ -f /usr/local/bin/create-filelist ]]; then
    # We're already here, but Justin Case wanted this
    cd "${PRODUCTION_ROOT}/" || { echo "Failed to change directory"; exit 1; }
    /bin/cp fullfiletimelist-rocky fullfiletimelist-rocky-old
    /usr/local/bin/create-filelist > fullfiletimelist-rocky
    cp fullfiletimelist-rocky fullfiletimelist
  fi
  # Full file list update for rocky linux itself
  cd "${PRODUCTION_ROOT}/${CATEGORY_STUB}/" || { echo "Failed to change directory"; exit 1; }
  # Hardlink everything except xml files
  echo "Hard linking"
  hardlink -x '.*\.xml.*' "${REVISION}"
  echo "Getting a full file list for the rocky dir"
  find . > fullfilelist
  if [[ -f /usr/local/bin/create-filelist ]]; then
    # We're already here, but Justin Case wanted this
    cd "${PRODUCTION_ROOT}/${CATEGORY_STUB}/" || { echo "Failed to change directory"; exit 1; }
    /bin/cp fullfiletimelist-rocky fullfiletimelist-rocky-old
    /usr/local/bin/create-filelist > fullfiletimelist-rocky
    cp fullfiletimelist-rocky fullfiletimelist
  fi
  chown 10004:10005 fullfilelist fullfiletimelist-rocky fullfiletimelist
fi

