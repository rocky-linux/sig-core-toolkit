#!/bin/bash
# Syncs everything from staging to production

if [[ "$RLREL" == "lh" ]] || [[ "$RLREL" == "beta" ]]; then
  echo "Lookahead nor Beta should be vaulted"
  exit 1
fi

# Source common variables
# shellcheck disable=SC2046,1091,1090
source "$(dirname "$0")/common"

REV=${REVISION}

cd "${PRODUCTION_ROOT}/${CATEGORY_STUB}" || { echo "Failed to change directory"; ret_val=1; exit 1; }
ret_val=$?

if [ $ret_val -eq "0" ]; then
  TARGET="${PRODUCTION_ROOT}/${VAULT_STUB}/${REV}"
  mkdir -p "${TARGET}"
  rsync_no_delete_prod "${REV}" "${TARGET}"
  echo "Syncing to the vault completed. Please run the file list script."
fi

