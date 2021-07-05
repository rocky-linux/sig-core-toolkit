#!/bin/bash
r_log "rocky" "Check /etc/rocky-release symbolic links"

grep -q "Rocky" /etc/rocky-release || r_checkExitStatus 1
(file /etc/redhat-release | grep -qE "symbolic link to .?rocky-release.?") && \
(file /etc/system-release | grep -qE "symbolic link to .?rocky-release.?")

r_checkExitStatus $?
