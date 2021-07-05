#!/bin/bash
r_log "perl" "Verify that perl is installed"
perl --version &> /dev/null
r_checkExitStatus $?
