#!/bin/bash
r_log "coreutils" "Testing basename"

# Doing two tests for validation
basename ./core/pkg_coreutils/11-basename.sh | grep -q 11-basename.sh
r_checkExitStatus $?

basename /etc/hosts | grep -q hosts
r_checkExitStatus $?
