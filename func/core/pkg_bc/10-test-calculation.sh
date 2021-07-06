#!/bin/bash
r_log "bc" "Testing simple calculations"
test "$(echo "8 + 5 * 2 / 10 - 1" | bc)" -eq "8"
r_checkExitStatus $?
