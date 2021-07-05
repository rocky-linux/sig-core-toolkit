#!/bin/bash
# Syncs everything from staging to production
REVISION=${1}
cd "/mnt/repos-staging/mirror/pub/rocky/${REVISION}"
ret_val=$?
if [ $ret_val -eq "0" ]; then
  mkdir -p "/mnt/repos-production/mirror/pub/rocky/${REVISION:0:3}"
  sudo -l && find **/* -maxdepth 0 -type d | parallel --will-cite -j 18 sudo rsync -av --chown=10004:10005 --progress --relative --human-readable {} /mnt/repos-production/mirror/pub/rocky/${REVISION:0:3}
else
  echo "Failed to change directory"
fi
