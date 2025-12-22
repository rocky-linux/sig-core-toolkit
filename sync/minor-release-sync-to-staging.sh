#!/bin/bash
# Performs a full on sync of a minor release, directories and all. It calls the
# other scripts in this directory to assist where necessary.
# Note that this is EL8, EL10+ only
#
# Source common variables
# shellcheck disable=SC2046,1091,1090
source $(dirname "$0")/common

# Major Version (eg, 8)
MAJ=${RLVER}

# sync all pieces of a release, including extras, nfv, etc
for COMPOSE in "${NONSIG_COMPOSE[@]}"; do
  echo "${COMPOSE}: Syncing"
  SYNCSRC="/mnt/compose/${MAJ}/latest-${COMPOSE}-${MAJ}"
  pushd "${SYNCSRC}/compose" || { echo "${COMPOSE}: Failed to change directory"; break; }

  if [[ "${COMPOSE}" == "Rocky" ]]; then
    # ISO Work before syncing
    for ARCH in "${ARCHES[@]}"; do
      mkdir -p "isos/${ARCH}"
    done

    # Sort the ISO's
    for ARCH in "${ARCHES[@]}"; do
      for x in "${ISO_TYPES[@]}"; do
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

      echo "Symlinking to 'latest' if ISO exists"
      test -f "Rocky-${REVISION}-${ARCH}-boot.iso" && ln -s "Rocky-${REVISION}-${ARCH}-boot.iso" "Rocky-${MAJ}-latest-${ARCH}-boot.iso"
      test -f "Rocky-${REVISION}-${ARCH}-dvd.iso" && ln -s "Rocky-${REVISION}-${ARCH}-dvd.iso" "Rocky-${MAJ}-latest-${ARCH}-dvd.iso"
      test -f "Rocky-${REVISION}-${ARCH}-dvd1.iso" && ln -s "Rocky-${REVISION}-${ARCH}-dvd1.iso" "Rocky-${MAJ}-latest-${ARCH}-dvd.iso"
      test -f "Rocky-${REVISION}-${ARCH}-minimal.iso" && ln -s "Rocky-${REVISION}-${ARCH}-minimal.iso" "Rocky-${MAJ}-latest-${ARCH}-minimal.iso"
      echo "(Re)generating manifests"
      for file in *.iso; do
        xorriso -dev "${file}" --find | tail -n+2 | tr -d "'" | cut -c2- | sort > "${file}.manifest"
      done

      # ISO checksums
      for file in *.iso; do
        printf "# %s: %s bytes\n%s\n" \
          "${file}" \
          "$(stat -c %s ${file} -L)" \
          "$(sha256sum --tag ${file})" \
        | sudo tee -a "${file}.CHECKSUM"
      done
      cat ./*.CHECKSUM > CHECKSUM
      # GPG sign the checksums
      popd || { echo "Could not change directory"; break; }
    done
    # Sort the cloud images here. Probably just a directory move, make some checksums (unless they're already there)
    # Live images should probably be fine. Check anyway what we want to do. Might be a simple move.
  fi
  # Delete the unnecessary dirs here.
  for EMPTYDIR in "${NONREPO_DIRS[@]}"; do
    rm -rf "${EMPTYDIR}"
  done
  popd || { echo "${COMPOSE}: Failed to change directory"; break; }

  TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}"
  mkdir -p "${TARGET}"
  pushd "${SYNCSRC}" || { echo "${COMPOSE}: Failed to change directory"; break; }
  if [[ "${COMPOSE}" != "Rocky" ]]; then
    rsync_no_delete_staging_with_excludes "${TARGET}" "metadata"
  else
    rsync_no_delete_staging "${TARGET}"
  fi
  popd || { echo "${COMPOSE}: Failed to change directory"; break; }
done

# Sync images, they are NOT part of the normal compose at the moment.
# mv everything from iso/* and images/* to base, rmdir
# if vagrant is in the name, rename them to drop the ending
# for x in $(ls) ; do if [[ "${x}" =~ "vagrant" ]]; then mv ${x} $(echo ${x} | sed 's/\.vagrant\..*\(\.box\)/\1/g') ; fi ; done
# create symlinks for live sed -E "s/${MAJOR}\.${MINOR}/${MAJOR}/g ; s/[0-9]+\.[0-9]+/latest/g"
# create symlinks for images for x in * ; do ln -s ${x} $(echo $x | sed -E 's/-10.0-[0-9]+\.[0-9]+/.latest/g ; s/\.oci//g') ; done
# remove original CHECKSUM file and then checksum everything
# cat all checksums into single files, sign it
# we need a separate script that can do this same stuff and not kill everything

# Create symlinks for repos that were once separate from the main compose
for LINK in "${!LINK_REPOS[@]}"; do
  ln -sr "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${LINK}" \
    "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${LINK_REPOS[$LINK]}"
done

# make a kickstart directory
for ARCH in "${ARCHES[@]}"; do
  for REPO in "${MODS_REPOS[@]}"; do
    SOURCE="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${REPO}/${ARCH}/os"
    TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${REPO}/${ARCH}/kickstart"
    echo "Making golden kickstart directory"
    rsync -vrlptDSH --chown=10004:10005 --progress --human-readable "${SOURCE}/" "${TARGET}"
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
for ARCH in "${ARCHES[@]}"; do
  for REPO in "${MODS_REPOS[@]}"; do
    OS_TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${REPO}/${ARCH}/os/repodata/repomd.xml"
    GOLD_TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${REPO}/${ARCH}/kickstart/repodata/repomd.xml"
    echo "Signing ${REPO} ${ARCH}"
    sign_data "${OS_TARGET}" "${MAJ}"
    sign_data "${GOLD_TARGET}" "${MAJ}"
  done
done

# Change Symlink if required
echo "Setting symlink to ${REV}"
pushd "${STAGING_ROOT}/${CATEGORY_STUB}" || exit
/bin/rm "${STAGING_ROOT}/${CATEGORY_STUB}/latest-${MAJ}"
ln -sr "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}" "latest-${MAJ}"
/bin/rm "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}"
ln -sr "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}" "${REVISION}"
echo "Attempting hard link"
perform_hardlink "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}"
popd || exit
