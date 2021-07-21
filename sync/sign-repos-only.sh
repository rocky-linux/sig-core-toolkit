#!/bin/bash
# Signs repo metadata only
# shellcheck disable=SC2046,1091,1090
source "$(dirname "$0")/common"

echo "** Signing source repos"
for y in "${ALL_REPOS[@]}"; do
  test -d "${STAGING_ROOT}/${RELEASE_DIR}/${y}/source/tree"
  ret_val=$?
  if [ "$ret_val" -eq 0 ]; then
    test -f /root/bin/sign-repo.sh && /root/bin/sign-repo.sh \
      "${STAGING_ROOT}/${RELEASE_DIR}/${y}/source/tree/repodata/repomd.xml"
  else
    echo "${STAGING_ROOT}/${RELEASE_DIR}/${y}/source/tree does not exist"
  fi
done

# Sync up some stuff
echo "** Signing arch repos as necessary **"
for x in "${ARCHES[@]}"; do
  # regular repos, no comps
  for y in "${NONMODS_REPOS[@]}"; do
    # os and debug/tree directories
    for z in os debug/tree; do
      test -d "${STAGING_ROOT}/${RELEASE_DIR}/${y}/${x}/${z}"
      ret_val=$?
      if [ "$ret_val" -eq 0 ]; then
        test -f /root/bin/sign-repo.sh && /root/bin/sign-repo.sh \
          "${STAGING_ROOT}/${RELEASE_DIR}/${y}/${x}/${z}/repodata/repomd.xml"
      else
        echo "${STAGING_ROOT}/${RELEASE_DIR}/${y}/${x}/${z} does not exist"
      fi
    done
  done
  # repos with comps/groups involved, but only debug
  for y in "${MODS_REPOS[@]}"; do
    test -d "${STAGING_ROOT}/${RELEASE_DIR}/${y}/${x}/debug/tree"
    ret_val=$?
    if [ "$ret_val" -eq 0 ]; then
      test -f /root/bin/sign-repo.sh && /root/bin/sign-repo.sh \
        "${STAGING_ROOT}/${RELEASE_DIR}/${y}/${x}/debug/tree/repodata/repomd.xml"
    else
      echo "${STAGING_ROOT}/${RELEASE_DIR}/${y}/${x}/debug/tree does not exist"
    fi
  done

  echo "** Sign all repos with comps/groups"
  for y in "${MODS_REPOS[@]}"; do
    echo "${y}: ${x}"
    test -d "${STAGING_ROOT}/${RELEASE_DIR}/${y}/${x}/os"
    ret_val=$?
    if [ "$ret_val" -eq 0 ]; then
      test -f /root/bin/sign-repo.sh && /root/bin/sign-repo.sh \
        "${STAGING_ROOT}/${RELEASE_DIR}/${y}/${x}/os/repodata/repomd.xml"
    else
      echo "${STAGING_ROOT}/${RELEASE_DIR}/${y}/${x}/os does not exist"
    fi
  done

  echo "** Sign module repos"
  for y in "${MODS[@]}"; do
    test -d "${STAGING_ROOT}/${RELEASE_DIR}/${y}/${x}/os"
    ret_val=$?
    if [ "$ret_val" -eq 0 ]; then
      # This might not be necessary, but it does not hurt incase repomd is modified
      test -f /root/bin/sign-repo.sh && /root/bin/sign-repo.sh \
        "${STAGING_ROOT}/${RELEASE_DIR}/${y}/${x}/os/repodata/repomd.xml"
    else
      echo "${STAGING_ROOT}/${RELEASE_DIR}/${y}/${x}/os does not exist"
    fi
  done
done
