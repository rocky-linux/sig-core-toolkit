#!/bin/bash
# Syncs everything from staging to production

# Source common variables
# shellcheck disable=SC2046,1091,1090
source "$(dirname "$0")/common"

REV=${REVISION}${APPEND_TO_DIR}

cd "${PRODUCTION_ROOT}/${SIG_CATEGORY_STUB}" || { echo "Failed to change directory"; ret_val=1; exit 1; }
ret_val=$?

if [ $ret_val -eq "0" ]; then
  # Full file list update for production root
  cd "${PRODUCTION_ROOT}/${SIG_CATEGORY_STUB}" || echo { echo "Failed to change directory"; exit 1; }
  echo "Starting full file list for root"
  find . > fullfilelist
  echo "Generating filelist for quick-fedora-mirror users"
  if [[ -f /usr/local/bin/create-filelist ]]; then
    # We're already here, but Justin Case wanted this
    cd "${PRODUCTION_ROOT}/" || { echo "Failed to change directory"; exit 1; }
    /bin/cp fullfiletimelist-sig fullfiletimelist-sig-old
    /usr/local/bin/create-filelist > fullfiletimelist-sig
    cp fullfiletimelist-sig fullfiletimelist
  fi
  chown 10004:10005 fullfilelist fullfiletimelist-sig fullfiletimelist
fi

