#!/bin/bash

# Source common variables
source "./common"

# Major Version (eg, 8)
MAJ=${1}
# Short name (eg, NFV, extras, Rocky, gluster9)
SHORT=${2}
# The directory where we're going to, usually MAJOR.MINOR, sometimes it's MAJOR.MINOR-RCX
REV=${3}
# Note, this should be lowercase. eg, storage.
SIG=${4}

cd /mnt/compose/${MAJ}/latest-${SHORT}-${MAJ}
ret_val=$?

if [ $ret_val -eq "0" ]; then
  local TARGET=${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/${SIG}
  mkdir -p ${TARGET}
  sudo -l && find **/* -maxdepth 0 -type d | parallel --will-cite -j 18 sudo rsync -av --chown=10004:10005 --progress --relative --human-readable \
      {} ${TARGET}
else
  echo "Failed to change directory"
fi
