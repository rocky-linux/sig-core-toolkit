#!/bin/bash
r_log "coreutils" "Testing timeout and sleep"
timeout 1 sleep 1
[ $? -eq 124 ] && timeout 2 sleep 2
[ $? -eq 124 ] && r_checkExitStatus $?
