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
  echo "Starting full file list for category"
  cd "${PRODUCTION_ROOT}/${CATEGORY_STUB}/" || { echo "Failed to change directory"; exit 1; }
  find . > "${PRODUCTION_ROOT}/${CATEGORY_STUB}/fullfilelist" & CATEPID=$!
  echo "Starting full file list for root"
  cd "${PRODUCTION_ROOT}/" || { echo "Failed to change directory"; exit 1; }
  find . > "${PRODUCTION_ROOT}/fullfilelist" & ROOTPID=$!
  echo "Starting full file list for sig"
  cd "${PRODUCTION_ROOT}/${SIG_CATEGORY_STUB}" || { echo "Failed to change directory"; exit 1; }
  find . > "${PRODUCTION_ROOT}/${SIG_CATEGORY_STUB}/fullfilelist" & SIGPID=$!

  wait $CATEPID
  wait $ROOTPID
  wait $SIGPID

  echo "Generating filelist for quick-fedora-mirror users"
  if [[ -f /usr/local/bin/create-filelist ]]; then
    # We're already here, but Justin Case wanted this
    cd "${PRODUCTION_ROOT}/${CATEGORY_STUB}/" || { echo "Failed to change directory"; exit 1; }
    /bin/cp fullfiletimelist-rocky fullfiletimelist-rocky-old
    /usr/local/bin/create-filelist > fullfiletimelist-rocky & CREALIPID=$!

    cd "${PRODUCTION_ROOT}/" || { echo "Failed to change directory"; exit 1; }
    /bin/cp fullfiletimelist-rocky fullfiletimelist-rocky-old
    /usr/local/bin/create-filelist > fullfiletimelist-rocky & ROOTLIPID=$!

    cd "${PRODUCTION_ROOT}/${SIG_CATEGORY_STUB}" || { echo "Failed to change directory"; exit 1; }
    /bin/cp fullfiletimelist-sig fullfiletimelist-sig-old
    /usr/local/bin/create-filelist > fullfiletimelist-sig & SIGLIPID=$!

    wait $CREALIPID
    wait $ROOTLIPID
    wait $SIGLIPID

    cd "${PRODUCTION_ROOT}/${CATEGORY_STUB}/" || { echo "Failed to change directory"; exit 1; }
    chown 10004:10005 fullfilelist fullfiletimelist-rocky fullfiletimelist fullfiletimelist-rocky-linux
    cp fullfiletimelist-rocky fullfiletimelist
    cp fullfiletimelist-rocky fullfiletimelist-rocky-linux

    cd "${PRODUCTION_ROOT}/" || { echo "Failed to change directory"; exit 1; }
    chown 10004:10005 fullfilelist fullfiletimelist-rocky fullfiletimelist
    cp fullfiletimelist-rocky fullfiletimelist

    cd "${PRODUCTION_ROOT}/${SIG_CATEGORY_STUB}" || { echo "Failed to change directory"; exit 1; }
    chown 10004:10005 fullfilelist fullfiletimelist-sig fullfiletimelist
    cp fullfiletimelist-sig fullfiletimelist
  fi
fi

