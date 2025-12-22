#!/bin/bash
# Performs a full on sync of a minor release, directories and all. It calls the
# other scripts in this directory to assist where necessary.
# Note that this is EL8 specific
#
# Source common variables
# shellcheck disable=SC2046,1091,1090
export SHORT=Rocky
export RLREL=lh
source $(dirname "$0")/common

# Major Version (eg, 8)
MAJ=${RLVER}

# sync all pieces of a release, including extras, nfv, etc
for COMPOSE in "${NONSIG_COMPOSE[@]}"; do
  echo "${COMPOSE}: Syncing"
  SYNCSRC="/mnt/compose/${MAJ}-LookAhead/latest-${COMPOSE}-${MAJ}"
  pushd "${SYNCSRC}/compose" || { echo "${COMPOSE}: Failed to change directory"; break; }

  if [[ "${COMPOSE}" == "Rocky" ]]; then
    # ISO Work before syncing
    for ARCH in "${ARCHES[@]}"; do
      mkdir -p "isos/${ARCH}"
    done

    # Sort the ISO's
    for ARCH in "${ARCHES[@]}"; do
      for x in "${ISO_TYPES[@]}"; do
        if [[ "${x}" != "BaseOS" ]]; then
          echo "${x} ${ARCH}: Removing unnecessary boot image"
          /bin/rm -v "${x}/${ARCH}/iso/Rocky-${REVISION}-20"*"${ARCH}"*.iso
        fi
        ## Check if the ISO even exists, if not skip
        if ls "${x}/${ARCH}/iso/"*.iso 1> /dev/null 2>&1; then
          echo "${x} ${ARCH}: Moving ISO images"
          mv "${x}/${ARCH}/iso/"* "isos/${ARCH}/"
        else
          echo "${x} ${ARCH}: No ISOs were found"
        fi
        echo "${x} ${ARCH}: Removing original ISO directory if applicable"
        test -d "${x}/${ARCH}/iso" && rmdir "${x}/${ARCH}/iso"
      done
      pushd "isos/${ARCH}" || { echo "${ARCH}: Failed to change directory"; break; }
      # ISO checksums
      for file in *.iso; do
        printf "# %s: %s bytes\n%s\n" \
          "${file}" \
          "$(stat -c %s ${file} -L)" \
          "$(sha256sum --tag ${file})" \
        | sudo tee -a "${file}.CHECKSUM"
      done
      cat ./*.CHECKSUM > CHECKSUM
      popd || { echo "Could not change directory"; break; }
    done
    # Sort the cloud images here. Probably just a directory move, make some checksums (unless they're already there)
    for ARCH in "${ARCHES[@]}"; do
      echo "${ARCH}: Sorting cloud images"
      if [ -d "images/${ARCH}" ]; then
        pushd "images/${ARCH}" || { echo "${ARCH}: Failed to change directory"; break; }
        mv images/* .
        rmdir images
        test -f CHECKSUM && /bin/rm CHECKSUM
        # Drop vagrant from name if they are there
        echo "${ARCH}: Looking for vagrant names and dropping them"
        for x in * ; do if [[ "${x}" =~ "vagrant" ]]; then mv "${x}" $(echo ${x} | sed 's/\.vagrant\..*\(\.box\)/\1/g') ; fi ; done
        # Generate "latest" links
        for x in * ; do ln -s "${x}" $(echo "${x}" | sed -E "s/-$REVISION-[0-9]+\.[0-9]+/.latest/g ; s/\.oci//g") ; done
        # Cloud checksums
        for file in *; do
          printf "# %s: %s bytes\n%s\n" \
            "${file}" \
            "$(stat -c %s ${file} -L)" \
            "$(sha256sum --tag ${file})" \
          | sudo tee -a "${file}.CHECKSUM"
        done
        cat ./*.CHECKSUM > CHECKSUM
        popd || { echo "${ARCH}: Failed to change directory"; break; }
      fi
    done
    # Live images should probably be fine. Check anyway what we want to do. Might be a simple move.
    for ARCH in "${ARCHES[@]}"; do
      echo "${ARCH}: Sorting live images"
      if [ -d "live/${ARCH}" ]; then
        pushd "live/${ARCH}" || { echo "${ARCH}: Failed to change directory"; break; }
        mv iso/* .
        rmdir iso
        test -f CHECKSUM && /bin/rm CHECKSUM
        # Generate "latest" links
        for x in * ; do ln -s "${x}" $(echo "${x}" | sed -E "s/${MAJOR}\.${MINOR}/${MAJOR}/g ; s/[0-9]+\.[0-9]+/latest/g") ; done
        # live checksums
        for file in *; do
          printf "# %s: %s bytes\n%s\n" \
            "${file}" \
            "$(stat -c %s ${file} -L)" \
            "$(sha256sum --tag ${file})" \
          | sudo tee -a "${file}.CHECKSUM"
        done
        cat ./*.CHECKSUM > CHECKSUM
        popd || { echo "${ARCH}: Failed to change directory"; break; }
      fi
    done
  fi
  # Delete the unnecessary dirs here.
  for EMPTYDIR in "${NONREPO_DIRS[@]}"; do
    rm -rf "${EMPTYDIR}"
  done
  popd || { echo "${COMPOSE}: Failed to change directory"; break; }

  TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}"
  UTILS="${STAGING_ROOT}/${CATEGORY_STUB}/utils/${MAJOR}"
  mkdir -p "${TARGET}"
  pushd "${SYNCSRC}" || { echo "${COMPOSE}: Failed to change directory"; break; }
  if [[ "${COMPOSE}" != "Rocky" ]]; then
    rsync_no_delete_staging_with_excludes "${TARGET}" "metadata"
  else
    if [ -d "${TARGET}/devel" ]; then
      echo "Moving devel directory temporarily..."
      mv "${TARGET}/devel" "${UTILS}/devel"
    fi
    echo "Begin syncing..."
    rsync_delete_staging "${TARGET}"
    if [ -d "${UTILS}/devel" ]; then
      echo "Moving devel back..."
      mv "${UTILS}/devel" "${TARGET}/devel"
    fi
  fi
  popd || { echo "${COMPOSE}: Failed to change directory"; break; }
done

# Create symlinks for repos that were once separate from the main compose
for LINK in "${!LINK_REPOS[@]}"; do
  ln -sr "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${LINK}" \
    "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${LINK_REPOS[$LINK]}"
done


# fix treeinfo
for ARCH in "${ARCHES[@]}"; do
  echo "Ensuring treeinfo is correct"
  treeinfoModder "${ARCH}"
  treeinfoSaver "${ARCH}"
done

# Change Symlink if required
echo "Setting symlink to ${REV}"
pushd "${STAGING_ROOT}/${CATEGORY_STUB}" || exit
/bin/rm "${STAGING_ROOT}/${CATEGORY_STUB}/${MAJ}-LookAhead"
ln -sr "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}" "${MAJ}-LookAhead"
echo "Attempting hard link"
perform_hardlink "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}"
popd || exit
