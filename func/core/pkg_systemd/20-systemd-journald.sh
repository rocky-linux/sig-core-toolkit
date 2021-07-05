#!/bin/bash
r_log "systemd" "Testing journalctl with a teststring"

currentTime=$(date +'%T')
testString=01092deadbeef9915710501deadbeef6
echo "${testString}" > /dev/kmsg
journalctl --since "${currentTime}" | grep -q "${testString}"

r_checkExitStatus $?
