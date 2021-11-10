#!/bin/bash

# Source common variables
# shellcheck disable=SC2046,1091,1090
source "$(dirname "$0")/common"

if [[ $# -eq 0 ]]; then
  echo "You must specify a short name."
  exit 1
fi

# For now, only architecture that we support live is x86_64
TARGET="${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/Live/x86_64"
mkdir -p "${TARGET}"

cat > "${TARGET}/README" <<EOF
This directory contains official live images for Rocky Linux. Some rely on the
use of EPEL (KDE and XFCE). As of this writing, the XFCE image does not come
with a default wallpaper. We have been unable to address this directly.

Please open a github issue for these live image kickstarts or a bug if there
are larger issues.

-label
EOF
