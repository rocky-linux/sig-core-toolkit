#!/bin/bash
# Major Version (eg, 8)
MAJOR=${1}
# Short name (eg, NFV, extras, Rocky, gluster9)
SHORT=${2}
# The directory where we're going to, usually MAJOR.MINOR, sometimes it's MAJOR.MINOR-RCX
REVISION=${3}
cd /mnt/compose/${MAJOR}/latest-${SHORT}-${MAJOR}
ret_val=$?
if [ $ret_val -eq "0" ]; then
  mkdir -p /mnt/repos-staging/mirror/pub/rocky/${REVISION}
  sudo -l && find **/* -maxdepth 0 -type d | parallel --will-cite -j 18 sudo rsync -av --chown=10004:10005 --progress --relative --human-readable {} /mnt/repos-staging/mirror/pub/rocky/${REVISION}
else
  echo "Failed to change directory"
fi
