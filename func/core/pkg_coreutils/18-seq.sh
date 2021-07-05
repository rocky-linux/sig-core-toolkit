#!/bin/bash
r_log "coreutils" "Testing seq"
seq -s " " 6 | grep -q "1 2 3 4 5 6" && \
seq -s " " 3 5 | grep -q "3 4 5" && \
seq -s " " 3 3 9 | grep -q "3 6 9"
r_checkExitStatus $?
