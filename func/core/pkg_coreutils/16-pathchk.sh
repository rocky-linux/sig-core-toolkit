#!/bin/bash
r_log "coreutils" "Testing pathchk"
pathchk -p "<>" 2> /dev/null
[ $? -eq 1 ] && pathchk /var/tmp/fakePathAndFile
[ $? -eq 0 ] && pathchk /var/tmp
r_checkExitStatus $?
