#!/bin/bash
r_log "coreutils" "Testing readlink"
trap "/bin/rm /var/tmp/listen" EXIT
ln -s /var/tmp/talk /var/tmp/listen
readlink /var/tmp/listen | grep -q "/var/tmp/talk"
r_checkExitStatus $?
