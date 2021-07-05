#!/bin/bash
r_log "kernel" "Testing the kernel keyring (GPG)"

ARCH=$(uname -m)
KERNEL=$(uname -r | cut -d'-' -f1)

if [ "${ARCH}" == "aarch64" ]; then
  r_log "kernel" "Architecture not tested: $ARCH"
  exit 0
fi

if [ "$RL_VER" -ge 8 ]; then
  ring=.builtin_trusted_keys
  for id in kpatch "Driver update" kernel; do
    r_log "kernel" "Verifying x.509 Rocky ${id}"
    keyctl list %:$ring | grep -i "REPLACE_ME" > /dev/null 2>&1
    r_checkExitStatus $?
  done
fi
