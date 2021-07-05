#!/bin/bash
r_log "setup" "Testing /etc/group file"
NOBODY=65534

grep -q "root:x:0" /etc/group && \
grep -q "bin:x:1" /etc/group && \
grep -q "daemon:x:2" /etc/group && \
grep -q "sys:x:3" /etc/group && \
grep -q "nobody:x:${NOBODY}" /etc/group

r_checkExitStatus $?
