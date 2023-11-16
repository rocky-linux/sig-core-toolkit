#!/bin/bash
# Syncs everything from production to vault

DATE="$(date +%Y%m%d%H%M%S)"

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
  rsync_no_delete_prod_no_repodata "${REV}" "${TARGET}"
fi

if [ "$RLVER" -eq "9" ]; then
  echo "copying module data"
  for repo in "${MODS[@]}"; do
    for arch in "${ARCHES[@]}"; do
      mkdir -p "${TARGET}/${repo}/${arch}/os/repodata"
      cp "${REV}/${repo}/${arch}/os/repodata/*MODULES.yaml.gz" "/tmp/${repo}-${arch}-${DATE}.modules.yaml.gz"
      pushd /tmp || exit 1
      gunzip "/tmp/${repo}-${arch}-${DATE}.modules.yaml.gz"
      popd || exit 1
      cp "/tmp/${repo}-${arch}-${DATE}.modules.yaml" "${TARGET}/${repo}/${arch}/os/repodata/"
    done
  done
  # groups
  for repo in "${MODS_REPOS[@]}"; do
    for arch in "${ARCHES[@]}"; do
      createrepo_comps "${TARGET}/${repo}/${arch}/os" "${REV}" "${REV}/${repo}/${arch}/os/repodata/*GROUPS.xml"
    done
  done
  # no groups
  for repo in "${NONMODS_REPOS[@]}"; do
    for arch in "${ARCHES[@]}"; do
      createrepo_update "${TARGET}/${repo}/${arch}/os" "${REV}"
      createrepo_update "${TARGET}/${repo}/${arch}/debug" "${REV}"
    done
  done
fi

echo "Syncing to the vault completed. Please run the file list script."
