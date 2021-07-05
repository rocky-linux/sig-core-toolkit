#!/bin/bash
r_log "setup" "Test /etc/shells"

grep -q 'bash' /etc/shells

r_checkExitStatus $?
