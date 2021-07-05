#!/bin/bash
r_log "coreutils" "Test head and tail"

r_log "coreutils" "Testing head"
head -n1 /etc/os-release | grep -q NAME
r_checkExitStatus $?

r_log "coreutils" "Testing tail"
tail -n1 /etc/os-release | grep -q SUPPORT
r_checkExitStatus $?
