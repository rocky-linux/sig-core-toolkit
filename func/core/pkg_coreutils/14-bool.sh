#!/bin/bash
r_log "coreutils" "Test true/false"

r_log "coreutils" "Test true"
true
test $? -eq 0
r_checkExitStatus $?

r_log "coreutils" "Test false"
false
test $? -eq 1
r_checkExitStatus $?
