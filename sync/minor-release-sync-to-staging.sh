#!/bin/bash
# Performs a full on sync of a minor release, directories and all. It calls the
# other scripts in this directory to assist where necessary.
# Note that this is EL8 specific
#
# Source common variables
# shellcheck disable=SC2046,1091,1090
source $(dirname "$0")/common

# Major Version (eg, 8)
MAJ=${RLVER}

# sync all pieces of a release, including extras, nfv, etc
for COMPOSE in "${NONSIG_COMPOSE[@]}"; do
  echo "${COMPOSE}: Syncing"
  pushd "/mnt/compose/${MAJ}/latest-${COMPOSE}-${MAJ}/compose" || { echo "${COMPOSE}: Failed to change directory"; break; }

  if [[ "${COMPOSE}" == "Rocky" ]]; then
    # ISO Work before syncing
    mkdir -p isos/{x86_64,aarch64}

    # Sort the ISO's
    for ARCH in "${ARCHES[@]}"; do
      for x in BaseOS Minimal; do
        echo "${x} ${ARCH}: Moving ISO images"
        mv "${x}/${ARCH}/iso/"* "isos/${ARCH}/"
      done
      pushd "isos/${ARCH}" || { echo "${ARCH}: Failed to change directory"; break; }
      ln -s "Rocky-${REVISION}-${ARCH}-boot.iso" "Rocky-${ARCH}-boot.iso"
      ln -s "Rocky-${REVISION}-${ARCH}-dvd1.iso" "Rocky-${ARCH}-dvd1.iso"
      ln -s "Rocky-${REVISION}-${ARCH}-dvd1.iso" "Rocky-${ARCH}-dvd.iso"
      ln -s "Rocky-${REVISION}-${ARCH}-minimal.iso" "Rocky-${ARCH}-minimal.iso"
      for file in *.iso; do
        printf "# %s: %s bytes\n%s\n" \
          "${file}" \
          "$(stat -c %s ${file})" \
          "$(sha256sum --tag ${file})" \
        | sudo tee -a CHECKSUM;
      done
      popd || { echo "Could not change directory"; break; }
    done
  fi

  TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}"
  mkdir -p "${TARGET}"
  # disabling because none of our files should be starting with dashes. If they
  # are something is *seriously* wrong here.
  # shellcheck disable=SC2035
  sudo -l && find **/* -maxdepth 0 -type d | parallel --will-cite -j 18 sudo rsync -av --chown=10004:10005 --progress --relative --human-readable \
      {} "${TARGET}"

  if [[ "${COMPOSE}" == "Rocky" ]]; then
    cp COMPOSE_ID "${TARGET}"
    chown 10004:10005 "${TARGET}/COMPOSE_ID"
    rsync -av --chown=10004:10005 --progress --relative --human-readable metadata "${TARGET}"
  fi

  # Return back to where we started
  popd || { echo "${COMPOSE}: Failed to change back"; break; }

  # Create extra stuff
  pushd "${TARGET}" || { echo "${COMPOSE}: Failed to change directory"; break;  }
  mkdir -p Live/x86_64
  ln -s Live live
  popd || { echo "${COMPOSE}: Failed to change back"; break;  }
done


# Create symlinks for repos that were once separate from the main compose
for LINK in "${LINK_REPOS[@]}"; do
  ln -sr "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${LINK}" \
    "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${LINK_REPOS[$LINK]}"
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
  treeinfoSaver "${ARCH}"
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
