#!/bin/bash
r_log "lsb" "Test LSB branding"
lsb_release -i | grep -q "Rocky"
r_checkExitStatus $?
lsb_release -d | grep -q "Rocky"
r_checkExitStatus $?
