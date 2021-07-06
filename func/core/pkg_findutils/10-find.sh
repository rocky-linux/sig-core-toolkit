#!/bin/bash
r_log "findutils" "Testing basic find stuff"

TMPDIR=/var/tmp/find

[ -e $TMPDIR ] && rm -rf "$TMPDIR"

mkdir -p "$TMPDIR" || { r_log "findutils" "Can't create $TMPDIR"; exit "$FAIL"; }
touch "$TMPDIR/file1"
touch "$TMPDIR/file with a space"
r_log "findutils" "Check that find just works(tm)"
find "$TMPDIR" &> /dev/null
r_checkExitStatus $?

r_log "findutils" "Check that find fails for something that doesn't exist"
find "$TMPDIR/doesntexit" &> /dev/null
if [ $? -ne 1 ]; then
  r_log "findutils" "Something wrong happened. Was the file there?"
else
  r_checkExitStatus 0
fi

r_log "findutils" "Prepare for xargs test"
LINES=$(find "$TMPDIR" -print0 | wc -l)

if [ "$LINES" -eq 0 ]; then
  r_checkExitStatus 0
else
  r_checkExitStatus 1
fi

r_log "findutils" "Perform for xargs test"
find "$TMPDIR" -type f -print0 | xargs -0 ls &> /dev/null
r_checkExitStatus $?

r_log "findutils" "Perform for xargs test: fails with spaces in the name"
# shellcheck disable=SC2038
find "$TMPDIR" -type f | xargs ls &> /dev/null && { r_log "findutils" "Why did this get a 0 exit?"; exit "$FAIL"; }
ret_val=$?
if [ "$ret_val" -ne 0 ]; then
  r_checkExitStatus $?
fi

rm -rf "$TMPDIR"
