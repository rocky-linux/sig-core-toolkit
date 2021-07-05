#!/bin/bash
r_log "shadow" "Verify the shadow-utils files exist"

r_log "shadow" "Verify /etc/default"
[ -d "/etc/default" ] || { r_log "shadow" "Missing /etc/default"; r_checkExitStatus 1; }
r_log "shadow" "Verify /etc/default/useradd"
[ -e "/etc/default/useradd" ] || { r_log "shadow" "Missing /etc/default/useradd"; r_checkExitStatus 1; }
r_log "shadow" "Verify /etc/login.defs"
[ -e "/etc/login.defs" ] || { r_log "shadow" "Missing /etc/login.defs"; r_checkExitStatus 1; }
r_checkExitStatus 0
