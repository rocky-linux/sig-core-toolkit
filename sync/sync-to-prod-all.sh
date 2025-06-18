#!/bin/bash
# Syncs every release at once (hardcoded)

if [ ! -f "sync-to-prod.sh" ]; then
  echo "Sync to prod script not in PWD."
  exit 1
fi

# Rocky Linux 8
RLVER=8 bash sync-to-prod.sh

# Rocky Linux 9
RLVER=9 bash sync-to-prod.sh

# Rocky Linux 10
RLVER=10 bash sync-to-prod.sh

# Updates the file lists
bash sync-file-list-parallel.sh

# 9 is still in peridot, so there's no downgradable packages
RLVER=9 bash vault-release-no-repodata.sh
