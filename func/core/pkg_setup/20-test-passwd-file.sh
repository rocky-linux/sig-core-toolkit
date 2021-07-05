#!/bin/bash
r_log "setup" "Testing /etc/passwd file"
NOBODY=65534

grep -q "root:x:0" /etc/passwd && \
grep -q "bin:x:1" /etc/passwd && \
grep -q "nobody:x:${NOBODY}" /etc/passwd

r_checkExitStatus $?
