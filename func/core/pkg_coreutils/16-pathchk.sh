#!/bin/bash
r_log "coreutils" "Testing pathchk"
pathchk -p "<>" 2> /dev/null
# shellcheck disable=SC2181
[ $? -eq 1 ] && pathchk /var/tmp/fakePathAndFile
# shellcheck disable=SC2181
[ $? -eq 0 ] && pathchk /var/tmp
r_checkExitStatus $?
