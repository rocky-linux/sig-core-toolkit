#!/bin/bash
r_log "coreutils" "Test cut command"

[ "$(cut -f1 -d ' ' /etc/redhat-release)" == "Rocky" ]
r_checkExitStatus $?
