#!/bin/bash
r_log "coreutils" "Check that the architecture matches"
uname -a | grep -q "$(arch)"
r_checkExitStatus $?
