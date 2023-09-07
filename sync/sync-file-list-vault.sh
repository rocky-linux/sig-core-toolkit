#!/bin/bash
# Syncs everything from staging to production

# Source common variables
# shellcheck disable=SC2046,1091,1090
source "$(dirname "$0")/common"
VAULT_ROOT="mirror/vault"

cd "${PRODUCTION_ROOT}/${VAULT_ROOT}/" || { echo "Failed to change directory"; ret_val=1; exit 1; }
ret_val=$?

if [ $ret_val -eq "0" ]; then
  echo "Starting full file list for main vault"
  cd "${PRODUCTION_ROOT}/${VAULT_ROOT}/" || { echo "Failed to change directory"; exit 1; }
  find . > "${PRODUCTION_ROOT}/${VAULT_ROOT}/fullfilelist" & CATEPID=$!
  echo "Starting full file list for rocky"
  cd "${PRODUCTION_ROOT}/${VAULT_ROOT}/rocky" || { echo "Failed to change directory"; exit 1; }
  find . > "${PRODUCTION_ROOT}/${VAULT_ROOT}/rocky/fullfilelist" & ROOTPID=$!

  wait $CATEPID
  wait $ROOTPID

  echo "Generating filelist for quick-fedora-mirror users"
  if [[ -f /usr/local/bin/create-filelist ]]; then
    # We're already here, but Justin Case wanted this
    cd "${PRODUCTION_ROOT}/${VAULT_ROOT}/" || { echo "Failed to change directory"; exit 1; }
    /usr/local/bin/create-filelist > fullfiletimelist-vault & CREALIPID=$!

    cd "${PRODUCTION_ROOT}/${VAULT_ROOT}/rocky" || { echo "Failed to change directory"; exit 1; }
    /usr/local/bin/create-filelist > fullfiletimelist-rocky-vault & ROOTLIPID=$!

    wait $CREALIPID
    wait $ROOTLIPID

    cd "${PRODUCTION_ROOT}/${VAULT_ROOT}/" || { echo "Failed to change directory"; exit 1; }
    chown 10004:10005 fullfilelist fullfiletimelist-vault
    cd "${PRODUCTION_ROOT}/${VAULT_ROOT}/rocky" || { echo "Failed to change directory"; exit 1; }
    chown 10004:10005 fullfilelist fullfiletimelist-rocky-vault
  fi
fi

