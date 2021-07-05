#!/bin/bash
r_log "postfix" "Test helo request"
echo "helo test" | nc -w 3 127.0.0.1 25 | grep -q '250'
r_checkExitStatus $?
