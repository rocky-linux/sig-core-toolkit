#!/bin/bash
r_log "lsb" "Install LSB package"
if [ "$RL_VER" -ge 8  ]; then
  r_log "lsb" "redhat-lsb is not in EL9"
  exit $PASS
fi

p_installPackageNormal redhat-lsb
