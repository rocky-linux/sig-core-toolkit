#!/bin/bash
# Performs a full on sync of a minor release, directories and all. It calls the
# other scripts in this directory to assist where necessary.
# Source common variables
# shellcheck disable=SC2046,1091,1090
source $(dirname "$0")/common

# Major Version (eg, 8)
MAJ=${RLVER}

# sync all pieces of a release, including extras, nfv, etc
for COMPOSE in Rocky "${NONMODS_REPOS[@]}"; do
  cd "/mnt/compose/${MAJ}/latest-${COMPOSE}-${MAJ}/compose" || { echo "${COMPOSE}: Failed to change directory"; break; }

  TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}"
  mkdir -p "${TARGET}"
  # disabling because none of our files should be starting with dashes. If they
  # are something is *seriously* wrong here.
  # shellcheck disable=SC2035
  sudo -l && find **/* -maxdepth 0 -type d | parallel --will-cite -j 18 sudo rsync -av --chown=10004:10005 --progress --relative --human-readable \
      {} "${TARGET}"
done

# sync all sig stuff
for SIG in "${!SIG_COMPOSE[@]}"; do
  cd "/mnt/compose/${MAJ}/latest-${SIG}-${MAJ}/compose" || { echo "${COMPOSE}: Failed to change directory"; break; }

  TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${SIG_COMPOSE[$SIG]}"
  mkdir -p "${TARGET}"
  # disabling because none of our files should be starting with dashes. If they
  # are something is *seriously* wrong here.
  # shellcheck disable=SC2035
  sudo -l && find **/* -maxdepth 0 -type d | parallel --will-cite -j 18 sudo rsync -av --chown=10004:10005 --progress --relative --human-readable \
      {} "${TARGET}"
done

# copy around the ISOs a bit, make things comfortable
for ARCH in "${ARCHES[@]}"; do
  TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/isos/${ARCH}"
  # who knows if EL9 will change the name of baseos
  for x in BaseOS Minimal; do
    SOURCE="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${x}/${ARCH}/iso"
    mkdir -p "${TARGET}"
    cp "${SOURCE}/*.iso" "${TARGET}"
    cp "${SOURCE}/*.iso.manifest" "${TARGET}"
    cat "${SOURCE}/CHECKSUM" >> "${TARGET}/CHECKSUM"
  done
done

# sign all repos
test -f $(dirname "$0")/sign-repos-only.sh
ret_val=$?

if [ "$ret_val" -eq 0 ]; then
  $(dirname "$0")/sign-repos-only.sh
fi
