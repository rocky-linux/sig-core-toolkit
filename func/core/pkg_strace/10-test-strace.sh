#!/bin/bash
r_log "strace" "Run basic strace tests"
/usr/bin/strace ls &> /dev/null
ret_val=$?

if [ "$ret_val" -ne 0 ]; then
  r_log "strace" "strace exited with a non-zero exit code"
  r_checkExitStatus 1
else
  r_checkExitStatus 0
fi
