#!/bin/bash
# Performs a full on sync of a minor release, directories and all. It calls the
# other scripts in this directory to assist where necessary.
# Source common variables
# shellcheck disable=SC2046,1091,1090
source $(dirname "$0")/common

# Major Version (eg, 8)
MAJ=${RLVER}

# sync all pieces of a release, including extras, nfv, etc
for COMPOSE in "${NONSIG_COMPOSE[@]}"; do
  echo "${COMPOSE}: Syncing"
  pushd "/mnt/compose/${MAJ}/latest-${COMPOSE}-${MAJ}/compose" || { echo "${COMPOSE}: Failed to change directory"; break; }

  TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}"
  mkdir -p "${TARGET}"
  # disabling because none of our files should be starting with dashes. If they
  # are something is *seriously* wrong here.
  # shellcheck disable=SC2035
  sudo -l && find **/* -maxdepth 0 -type d | parallel --will-cite -j 18 sudo rsync -av --chown=10004:10005 --progress --relative --human-readable \
      {} "${TARGET}"

  # Return back to where we started
  popd || { echo "${COMPOSE}: Failed to change back"; break; }
done


# sync all sig stuff
# Disabled as we will have a different method for sig content and sig content
# is available upstream.
#for SIG in "${!SIG_COMPOSE[@]}"; do
#  echo "${SIG}: Syncing"
#  cd "/mnt/compose/${MAJ}/latest-${SIG}-${MAJ}/compose" || { echo "${COMPOSE}: Failed to change directory"; break; }
#
#  TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${SIG_COMPOSE[$SIG]}"
#  mkdir -p "${TARGET}"
#  # disabling because none of our files should be starting with dashes. If they
#  # are something is *seriously* wrong here.
#  # shellcheck disable=SC2035
#  sudo -l && find **/* -maxdepth 0 -type d | parallel --will-cite -j 18 sudo rsync -av --chown=10004:10005 --progress --relative --human-readable \
#      {} "${TARGET}"
#done

# copy around the ISOs a bit, make things comfortable
for ARCH in "${ARCHES[@]}"; do
  TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/isos/${ARCH}"
  # who knows if EL10 will change the name of baseos
  for x in BaseOS Minimal; do
    echo "${x} ${ARCH}: Copying ISO images"
    # Hardcoding this for now
    SOURCE="/mnt/compose/${MAJ}/latest-Rocky-${MAJ}/compose/${x}/${ARCH}/iso"
    TARGET_ARCH="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${x}/${ARCH}/iso"
    mkdir -p "${SOURCE}" "${TARGET}" "${TARGET_ARCH}"
    # Copy the ISO and manifests into their target architecture
    cp -n "${SOURCE}"/*.iso "${TARGET_ARCH}/"
    cp -n "${SOURCE}"/*.iso.manifest "${TARGET_ARCH}/"
    cp -n "${SOURCE}/CHECKSUM" "${TARGET_ARCH}/"
    # Copy the ISO and manifests into the main isos target
    cp "${SOURCE}"/*.iso "${TARGET}/"
    cp "${SOURCE}"/*.iso.manifest "${TARGET}/"
    pushd "${TARGET}" || { echo "Could not change directory"; break; }
    # shellcheck disable=SC2086
    for file in *.iso; do
      printf "# %s: %s bytes\n%s\n" \
        "${file}" \
        "$(stat -c %s ${file})" \
        "$(sha256sum --tag ${file})" \
      | sudo tee -a CHECKSUM;
    done
    popd || { echo "Could not change directory"; break; }
  done
done

# make a kickstart directory
for ARCH in "${ARCHES[@]}"; do
  for REPO in "${MODS_REPOS[@]}"; do
    SOURCE="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${REPO}/${ARCH}/os"
    TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${REPO}/${ARCH}/kickstart"
    echo "Making golden kickstart directory"
    cp -na "${SOURCE}" "${TARGET}"
  done
done

# fix treeinfo
for ARCH in "${ARCHES[@]}"; do
  echo "Ensuring treeinfo is correct"
  treeinfoModder "${ARCH}"
  treeinfoModderKickstart "${ARCH}"
done

# sign all repos
echo "Signing all repositories"
test -f $(dirname "$0")/sign-repos-only.sh
ret_val=$?

if [ "$ret_val" -eq 0 ]; then
  $(dirname "$0")/sign-repos-only.sh
fi

# Change Symlink if required
echo "Setting symlink to ${REV}"
pushd "${STAGING_ROOT}/${CATEGORY_STUB}" || exit
/bin/rm "${STAGING_ROOT}/${CATEGORY_STUB}/latest-8"
ln -sr "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}" latest-8
popd || exit
