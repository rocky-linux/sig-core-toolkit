#!/bin/bash
r_log "lsb" "Test LSB branding"
if [ "$RL_VER" -ge 8   ]; then
  r_log "lsb" "redhat-lsb is not in EL9"
  exit $PASS
fi

lsb_release -i | grep -q "Rocky"
r_checkExitStatus $?
lsb_release -d | grep -q "Rocky"
r_checkExitStatus $?
