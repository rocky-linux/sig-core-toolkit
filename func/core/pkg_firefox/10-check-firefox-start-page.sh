#!/bin/bash
r_log "firefox" "Check that the firefox startup page is correct"

if p_getPackageArch firefox | grep -q x86_64; then
  FIREPATH='/usr/lib64/firefox/defaults/preferences/all-redhat.js'
else
  FIREPATH='/usr/lib/firefox/defaults/preferences/all-redhat.js'
fi

COUNTS="$(grep -c rockylinux.org $FIREPATH)"

if [ "$COUNTS" -ge 2 ]; then
  r_checkExitStatus 0
else
  r_checkExitStatus 1
fi
