#!/bin/bash
r_log "which" "Testing that which can find bash"
/usr/bin/which bash | grep -Eq '^(/usr)?/bin/bash$'
r_checkExitStatus $?

r_log "which" "Testing that which fails on a command that doesn't exist"
/usr/bin/which obsidiaN 2> /dev/null
[ $? -eq 1 ] || { r_log "which" "Which should have failed." ; exit "$FAIL"; }
r_checkExitStatus $?
