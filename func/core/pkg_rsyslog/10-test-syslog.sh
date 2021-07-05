#!/bin/bash
r_log "rsyslog" "Verify that rsyslog is working as intended"
logger "$0 says Green Obsidian"

sleep 3

grep -q "Green Obsidian" /var/log/messages
r_checkExitStatus $?
