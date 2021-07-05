#!/bin/bash
r_log "telnet" "Basic telnet test"

telnet_sshd_test=`telnet 127.0.0.1 22 << EOF
EOF`

echo "$telnet_sshd_test" | grep -q "Escape character is '^]'"
r_checkExitStatus $?
