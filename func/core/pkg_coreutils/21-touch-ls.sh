#!/bin/bash
r_log "coreutils" "Testing touch and ls"

r_log "coreutils" "Touch files with specific dates"
touch -t 199104230420 /tmp/touch-1
touch -t 199104240420 /tmp/touch-2

r_log "coreutils" "Verify that the oldest file is last"
ls -lt /tmp/touch-? | tail -n 1 | grep -q 'touch-1'

r_checkExitStatus $?

/bin/rm /tmp/touch-?
