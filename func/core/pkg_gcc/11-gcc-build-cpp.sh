#!/bin/bash
r_log "gcc" "Ensure g++ can build a simple program"
OUTPUTPROG=$(mktemp)

g++ -x c++ ./common/files/hello.cpp -o "$OUTPUTPROG"
"$OUTPUTPROG" | grep -q "Hello!"
r_checkExitStatus $?

rm "$OUTPUTPROG"
