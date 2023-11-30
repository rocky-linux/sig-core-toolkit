#!/bin/bash
# Check that the release package is 1.X
r_log "rocky release" "Checking that the package is at least X.Y-1.B"

RELEASE_VER="$(rpm -q rocky-release --qf '%{RELEASE}')"
RELNUM="${RELEASE_VER:0:1}"
if [ "${RELNUM}" -ge "1" ]; then
  if [[ "${RELEASE_VER:0:3}" =~ ^${RELNUM}.[[:digit:]] ]]; then
    ret_val="0"
  else
    r_log "rocky release" "FAIL: The release package is not in X.Y-A.B format"
    ret_val="1"
  fi
else
    r_log "rocky release" "FAIL: The release package likely starts with 0 and is not considered production ready."
  ret_val="1"
fi

r_checkExitStatus $ret_val
