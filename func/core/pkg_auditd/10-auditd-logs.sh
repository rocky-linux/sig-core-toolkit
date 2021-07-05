#!/bin/bash
r_log "auditd" "Check if the audit logs are not empty"
[[ -s /var/log/audit/audit.log ]]
r_checkExitStatus $?
