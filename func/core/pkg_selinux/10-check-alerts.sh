#!/bin/bash
r_log "selinux" "Check for SELinux AVC alerts"
grep -v "AVC" /var/log/audit/audit.log > /dev/null 2>&1
r_checkExitStatus $?
