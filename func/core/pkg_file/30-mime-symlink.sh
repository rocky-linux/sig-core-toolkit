#!/bin/bash
r_log "file" "Check that we can see a symlink"
FILE_PATH=/var/tmp/linktest
MIME="inode/symlink"
ln -s /etc/issue $FILE_PATH
file -i $FILE_PATH | grep -q "${MIME}"
r_checkExitStatus $?

/bin/rm /var/tmp/linktest
