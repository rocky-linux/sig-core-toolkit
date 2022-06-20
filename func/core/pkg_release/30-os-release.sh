#!/bin/bash
r_log "rocky" "Check /etc/os-release stuff"

r_log "rocky" "Verify support directives"
for s in NAME=\"Rocky\ Linux\" \
  ID=\"rocky\" \
  ROCKY_SUPPORT_PRODUCT=\"Rocky-Linux-$RL_VER\" \
  ROCKY_SUPPORT_PRODUCT_VERSION=\"$RL_VER\"; do
  if ! grep -q "$s" /etc/os-release; then
    r_log "rocky" "Missing string ($s) in /etc/os-release"
    r_checkExitStatus 1
  fi
done
