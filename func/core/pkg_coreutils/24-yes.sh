#!/bin/bash
r_log "coreutils" "Test the yes command"

touch /var/tmp/yes-123
touch /var/tmp/yes-345
# shellcheck disable=SC2216
yes | /bin/rm -i /var/tmp/yes-* || r_checkExitStatus 1

deleted=1
test -f /var/tmp/yes-123 || test -f /var/tmp/yes-345 || deleted=0
r_checkExitStatus $deleted
