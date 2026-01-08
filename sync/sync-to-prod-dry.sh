#!/bin/bash
# Syncs everything from staging to production

if [[ "$RLREL" == "lh" ]] || [[ "$RLREL" == "beta" ]]; then
  exit 1
fi

# Source common variables
# shellcheck disable=SC2046,1091,1090
source "$(dirname "$0")/common"

REV=${REVISION}${APPEND_TO_DIR}

cd "${STAGING_ROOT}/${CATEGORY_STUB}" || { echo "Failed to change directory"; ret_val=1; exit 1; }
ret_val=$?

if [ $ret_val -eq "0" ]; then
  TARGET="${PRODUCTION_ROOT}/${CATEGORY_STUB}/${REV/-*/}"
  mkdir -p "${TARGET}"
  rsync_delete_prod_dry "${REV}" "${TARGET}"
  echo "Dry sync complete"
fi

