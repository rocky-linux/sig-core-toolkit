#!/bin/bash
r_log "auditd" "Generate events for audit log"

r_log "auditd" "Add test user"
useradd relengauditd
grep "ADD_USER" /var/log/audit/audit.log | grep -q 'acct="relengauditd"'
r_checkExitStatus $?

r_log "auditd" "Delete test user"
userdel relengauditd
grep "DEL_USER" /var/log/audit/audit.log | grep -q 'ID="relengauditd"'
r_checkExitStatus $?
