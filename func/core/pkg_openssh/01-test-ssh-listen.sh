#!/bin/bash
r_log "openssh" "Ensure ssh is listening"

echo "" > /dev/tcp/localhost/22
r_checkExitStatus $?
