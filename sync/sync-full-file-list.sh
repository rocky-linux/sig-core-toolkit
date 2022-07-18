#!/bin/bash
# Syncs everything from staging to production

# Source common variables
# shellcheck disable=SC2046,1091,1090
source "$(dirname "$0")/common"

REV=${REVISION}${APPEND_TO_DIR}

cd "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}" || { echo "Failed to change directory"; ret_val=1; exit 1; }
ret_val=$?

if [ $ret_val -eq "0" ]; then
  # Full file list update for rocky linux itself
  cd "${PRODUCTION_ROOT}/${CATEGORY_STUB}/" || { echo "Failed to change directory"; exit 1; }
  # Hardlink everything except xml files
  #hardlink -x '.*\.xml.*' "${REVISION}"
  echo "Starting full file list for category"
  find . > fullfilelist
  echo "Generating filelist for quick-fedora-mirror users"
  if [[ -f /usr/local/bin/create-filelist ]]; then
    # We're already here, but Justin Case wanted this
    cd "${PRODUCTION_ROOT}/${CATEGORY_STUB}/" || { echo "Failed to change directory"; exit 1; }
    /bin/cp fullfiletimelist-rocky fullfiletimelist-rocky-old
    /usr/local/bin/create-filelist > fullfiletimelist-rocky
    cp fullfiletimelist-rocky fullfiletimelist
    cp fullfiletimelist-rocky fullfiletimelist-rocky-linux
  fi
  chown 10004:10005 fullfilelist fullfiletimelist-rocky fullfiletimelist fullfiletimelist-rocky-linux
fi

