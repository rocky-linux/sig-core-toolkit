#!/bin/bash
r_log "auditd" "Install auditd (this should be available during minimal)"
p_installPackageNormal audit
r_log "auditd" "Ensure auditd is running and enabled"
# Ignore service cycler, auditd refuses manual stop
/usr/sbin/service auditd restart
sleep 2
/usr/bin/systemctl status auditd.service | grep -q "active"
r_checkExitStatus $?
