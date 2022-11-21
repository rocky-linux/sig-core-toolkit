#!/bin/bash
r_log "archive" "Testing znew"

TESTFILE=/var/tmp/znew.txt
/bin/rm $TESTFILE* &>/dev/null

ls -l /usr/bin > $TESTFILE
compress $TESTFILE

znew $TESTFILE.Z
r_checkExitStatus $?
