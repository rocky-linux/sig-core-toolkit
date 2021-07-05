#!/bin/bash
r_log "systemd" "Checking that systemctl can verify if a service is enabled"

# sshd is part of a minimal install
systemctl is-enabled sshd.service > /dev/null

r_checkExitStatus $?
