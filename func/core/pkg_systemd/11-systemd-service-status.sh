#!/bin/bash
r_log "systemd" "Checking if systemctl can check service status"

systemctl is-active sshd.service > /dev/null

r_checkExitStatus $?
