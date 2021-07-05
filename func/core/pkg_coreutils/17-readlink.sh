#!/bin/bash
r_log "coreutils" "Testing readlink"
ln -s /var/tmp/talk /var/tmp/listen
readlink /var/tmp/listen | grep -q "/var/tmp/talk"
r_checkExitStatus $?
/bin/rm /var/tmp/listen
