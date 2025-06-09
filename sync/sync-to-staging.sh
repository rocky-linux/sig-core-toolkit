#!/bin/bash

# Short name (eg, NFV, extras, Rocky, gluster9)
SHORT=${1}

# Source common variables
# shellcheck disable=SC2046,1091,1090
source "$(dirname "$0")/common"

if [[ $# -eq 0 ]]; then
  echo "You must specify a short name."
  exit 1
fi

if [[ "${RLVER}" -eq "8" ]]; then
  echo "This is only used for Rocky Linux 8 and 10 releases."
fi

# Major Version (eg, 8)
#MAJ=${RLVER}

#cd "${RELEASE_COMPOSE_ROOT}/compose" || { echo "Failed to change directory"; ret_val=1; exit 1; }
cd "${RELEASE_COMPOSE_ROOT}/" || { echo "Failed to change directory"; ret_val=1; exit 1; }
ret_val=$?

if [ $ret_val -eq "0" ]; then
  TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}"
  # The target should already exist as this is used to do simple syncs.
  mkdir -p "${TARGET}"

  # Find all directories for this compose
  mapfile -t repo_dirs < <(find compose -name repodata -type d | sed 's/compose\///g')
  mapfile -t src_dirs < <(find compose -name repodata -type d | sed 's/compose\///g ; s/\/repodata//g' | grep source)
  mapfile -t arch_dirs < <(find compose -name repodata -type d | sed 's/compose\///g ; s/\/repodata//g' | grep -v source)
  mapfile -t debug_dirs < <(find compose -name repodata -type d | sed 's/compose\///g ; s/\/repodata//g' | grep debug)

  # Delete all repodata for this compose
  echo "** Removing all current repo data"
  for x in "${repo_dirs[@]}"; do
    test -d "${TARGET}/${x}"
    ret_val=$?
    if [ $ret_val -eq "0" ]; then
      /bin/rm "${TARGET:?}/${x}/"*
    else
      echo "${x} not found"
    fi
  done

  # Now that we've deleted the repo data, we need to sync
  echo "** Syncing all new content"
  rsync_no_delete_staging_pungi "${TARGET}"

  # Now we need to createrepo
  echo "** Running createrepo on source repos"
  for src_repo in "${src_dirs[@]}"; do
    echo "Trying ${src_repo}..."
    test -d "${TARGET}/${src_repo}"
    ret_val=$?
    if [ $ret_val -eq "0" ]; then
      createrepo_update "${TARGET}/${src_repo}" "${MAJOR}"
      fix_metadata "${TARGET}/${src_repo}/repodata/repomd.xml"
      sign_data "${TARGET}/${src_repo}/repodata/repomd.xml" "${RLVER}"
    else
      echo "${src_repo} not found"
    fi
  done

  # We need to be specific here. If the short name is "Rocky" we have extra
  # work. Otherwise, normal createrepo is fine.
  echo "** Running createrepo on arch repos"
  if [[ "${SHORT}" == "Rocky" ]]; then
    echo "** Updating all debug repos"
    for debug_repo in "${debug_dirs[@]}"; do
      echo "Trying ${debug_repo}..."
      test -d "${TARGET}/${debug_repo}"
      ret_val=$?
      if [ $ret_val -eq "0" ]; then
        createrepo_update "${TARGET}/${debug_repo}" "${MAJOR}"
        fix_metadata "${TARGET}/${debug_repo}/repodata/repomd.xml"
        sign_data "${TARGET}/${debug_repo}/repodata/repomd.xml" "${RLVER}"
      else
        echo "${debug_repo} not found"
      fi
    done

    echo "** Updating all repos with comps/groups"
    for arch in "${ARCHES[@]}"; do
      for comp_repo in "${MODS_REPOS[@]}"; do
        echo "Trying ${arch} ${comp_repo}..."
        REPO_PATH="${TARGET}/${comp_repo}/${arch}/os"
        COMP_PATH="${RELEASE_COMPOSE_ROOT}/work/${arch}/comps/comps-${comp_repo}.${arch}.xml"
        test -d "${REPO_PATH}"
        ret_val=$?
        if [ $ret_val -eq "0" ]; then
          createrepo_comps "${REPO_PATH}" "${MAJOR}" "${COMP_PATH}"
          fix_metadata "${REPO_PATH}/repodata/repomd.xml"
          sign_data "${REPO_PATH}/repodata/repomd.xml" "${RLVER}"
        else
          echo "${comp_repo} not found"
        fi
      done
    done

    echo "** Updating modules if applicable"
    for arch in "${ARCHES[@]}"; do
      for mod_repo in "${MODS[@]}"; do
        echo "Trying ${arch} ${mod_repo}..."
        MOD_PATH="${TARGET}/${mod_repo}/${arch}/os/repodata"
        MOD_YAML="/mnt/compose/${RLVER}_metadata/${arch}/${mod_repo}-modules.yaml"
        test -f "${MOD_YAML}"
        ret_val=$?
        if [ $ret_val -ne 0 ]; then
          echo "Module yaml not found"
          continue
        fi

        test -d "${MOD_PATH}"
        ret_val=$?

        if [ $ret_val -eq 0 ]; then
          modifyrepo_module "${MOD_PATH}" "${MOD_YAML}"
          fix_metadata "${MOD_PATH}/repomd.xml"
          sign_data "${MOD_PATH}/repomd.xml" "${RLVER}"
        else
          echo "${mod_repo} not found"
        fi
      done
    done
  else
    for arch_repo in "${arch_dirs[@]}"; do
      echo "Trying ${arch_repo}..."
      test -d "${TARGET}/${arch_repo}"
      ret_val=$?
      if [ $ret_val -eq "0" ]; then
        createrepo_update "${TARGET}/${arch_repo}" "${MAJOR}"
        fix_metadata "${TARGET}/${arch_repo}/repodata/repomd.xml"
        sign_data "${TARGET}/${arch_repo}/repodata/repomd.xml" "${RLVER}"
      else
        echo "${arch_repo} not found"
      fi
    done
  fi

  if [[ "${SHORT}" == "Rocky" ]]; then
    echo "** Hardlinking staging directory (${TARGET})"
    perform_hardlink "${TARGET}"
  fi
  echo "** Syncing completed"
fi
