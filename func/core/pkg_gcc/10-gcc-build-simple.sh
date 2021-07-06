#!/bin/bash
r_log "gcc" "Ensure gcc can build a simple program"
OUTPUTPROG=$(mktemp)

gcc ./common/files/hello.c -o "$OUTPUTPROG"
"$OUTPUTPROG" | grep -q "Hello!"
r_checkExitStatus $?

rm "$OUTPUTPROG"
