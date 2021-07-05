#!/bin/bash
r_log "systemd" "Checking if systemctl can see enabled status for non-native services"
systemctl is-enabled kdump.service 2> /dev/null | grep -qE 'disabled|enabled'

r_checkExitStatus $?
