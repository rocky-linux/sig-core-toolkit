#!/bin/bash
r_log "kernel" "Testing debrand"

strings "/boot/vmlinuz-$(uname -r)" | grep -qi rhel
ret_val=$?

if [ "$ret_val" -eq "0" ]; then
  r_log "kernel" "Kernel does not appear to be debranded"
  r_checkExitStatus 1
else
  r_checkExitStatus 0
fi
